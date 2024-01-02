document.addEventListener('alpine:init', () => { 
    const isarray = Array.isArray;
    Alpine.data('projects_store', () => ({
        projects :   [],
        search_results : {},

        init () {
            this.update_store();
        },

        register (project, attr) {
            this.search_results[attr] = {results: []}
        },

        update_store () { 
            var _this = this;
            GETjson("{{url("core:rest", kwargs={"m" : "project.Project" })}}").then(
                json => this.projects = (isarray(json) ? json : [json]).map(x=>{
                    x.adding = {}
                    return x;
                })
            );
        },

        edit_value (project,attr) {
            // TODO what's going on with this line
            this.projects.forEach(x=>x.adding[attr] = false);
            // reset any possible previous state values 
            for (i in this.projects){
                for (key in this.projects[i].adding){
                    this.projects[i].adding[key] = false;
                }
            }
            // change state of adding to just current attr
            project.adding[attr] = true;
            // get ref to input element, can't use alpine refs for dynamically created elements
            el = htmx.find(`#${attr}_input`+project.id);
            // focus the input element
            this.$nextTick( ()=> el.focus() );
            // reset the input value
            el.value = ""
            // reset the results catalogue
            this.search_results[attr] = {results: []};
            // do a default search with empty value
            this.search_attr(project,attr,el);
        },

        cancel_edit_value (project, attr){
            project.adding[attr] = false;
        },

        search_attr ( project, attr, el){
            const _this = this;
            const url = `/core/text_ac/project.Project/${project.id}/${attr}/`;
            POST(url, new FormData(el.form), json_response=true ).then(
                resp => {
                    resp.json().then( data => {
                        let current_pks;
                        if (isarray(project[attr])) {
                            current_pks = project[attr].map(x=>x.id);
                        } else {
                            current_pks = project[attr] ?  [project[attr].id] : [];
                        }
                        for (var i in data["results"]){
                            const datum =  data["results"][i]
                            datum.selected =  current_pks.includes(datum.id)
                        }
                        _this.search_results[attr] = data 
                    })
                }
            )
        },

        toggle_attr(project,attr,result){
            const _this = this;
            const el = htmx.find(`#${attr}_input`+project.id);
            if (result.selected){
                if (result.id && isarray(project[attr])) {
                    project[attr] = project[attr].filter(x=> x.id != result.id);
                } else if (result.id){
                    project[attr] = undefined;
                }
                DELETE(result.url).then(x=>_this.update_store());
            } else {
                if (isarray(project[attr])) {
                    project[attr] = [...project[attr], result];
                } else {
                    project[attr] = [ result];
                }
                POST(result.url, new FormData(el.form)).then(x=>_this.update_store());
            }
            _this.cancel_edit_value(project,attr);
        }
    }));
});


