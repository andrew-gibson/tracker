document.addEventListener('alpine:init', () => { 
    const isarray = Array.isArray;
    Alpine.data('projects_store', (project,update_url, search_url) => ({
        project,

        update_store () { 
            var _this = this;
            GETjson(update_url).then( json => _this.project = json);
        },

        edit_value (attr) {
            this.$store.projects.active_edit = this.project.id + attr;
            this.$store.projects.set_search_results();
            // get ref to input element, can't use alpine refs for dynamically created elements
            const el = htmx.find(`#${attr}_input${this.project.id}`);
            // focus the input element
            this.$nextTick( ()=> el.focus() );
            // reset the input value
            el.value = ""
            // do a default search with empty value
            this.search_attr(attr,el);
        },

        cancel_edit_value ( attr){
            this.$store.projects.active_edit = "";
            this.$store.projects.set_search_results();
        },

        search_attr ( attr, el){
            const _this = this;
            let current_pks;
            if (isarray(this.project[attr])) {
                current_pks = this.project[attr].map(x=>x.id);
            } else {
                current_pks = this.project[attr] ?  [this.project[attr].id] : [];
            }
            const url = search_url.replace("__replace__",attr)

            POST(url, new FormData(el.form), json_response=true ).then(
                resp => {
                    resp.json().then( data => {
                        for (var i in data["results"]){
                            const datum =  data["results"][i]
                            datum.selected =  current_pks.includes(datum.id)
                        }
                        _this.$store.projects.set_search_results( data );
                    })
                }
            )
        },

        toggle_attr(attr,result){
            const _this = this;
            const el = htmx.find(`#${attr}_input${this.project.id}`);
            if (result.selected){
                if (result.id && isarray(this.project[attr])) {
                    this.project[attr] = this.project[attr].filter(x=> x.id != result.id);
                } else if (result.id){
                    this.project[attr] = undefined;
                }
                DELETE(result.url).then(x=>_this.update_store());
            } else {
                if (isarray(this.project[attr])) {
                    this.project[attr] = [...this.project[attr], result];
                } else {
                    this.project[attr] = [ result];
                }
                POST(result.url, new FormData(el.form)).then(x=>_this.update_store());
            }
            _this.cancel_edit_value(attr);
        }
    }));
});


