((model_name)=> {

    document.addEventListener('alpine:init', () => { 
        const isarray = Array.isArray;

        Alpine.store(model_name, {
            active_edit : "",
            search_results : {results : []},
            set_search_results (new_results = {results : []}) {
                this.search_results = new_results;
            }
        });

        Alpine.data(model_name, (model,update_url, search_url) => ({
            model,
            fields : {{dumps(model.form_fields_map)|safe}},

            input_type(attr){
                sql_type = this.fields[attr];
                input_type = this.input_lookup[sql_type]
            
            },

            update_model () { 
                var _this = this;
                GETjson(update_url).then( json => _this.imodel= json);
            },

            send_model () {
                const _this = this;
                const send_data = {};
                for (var x in this.fields){
                    if (["ManyToOneRel", "ManyToManyField"].includes(this.fields[x]) ){
                        val =  (this.model[x] || []).map(x=>x.id);
                        if (val.length) {
                          send_data[x] = val;
                        }
                    }  else if (this.fields[x] == "ForeignKey" ){
                       val = (this.model[x] || {}).id || "";
                        if (val){
                          send_data[x] = val;
                        }
                    } else {
                       send_data[x] = this.model[x] || "";
                    }
                }
                PUT(update_url, 
                    new URLSearchParams(send_data).toString(), 
                    json_response=true ).then(
                        resp => {
                            resp.json().then( data => {
                               _this.model = data;
                            });
                        }
                    );
            },

            edit_value (attr,el) {
                this.send_model()
            },

            edit_fk_value (attr) {
                this.$store[model_name].active_edit = this.model.id + attr;
                this.$store[model_name].set_search_results();
                // get ref to input element, can't use alpine refs for dynamically created elements
                const el = htmx.find(`#${attr}_input${this.model.id}`);
                // focus the input element
                this.$nextTick( ()=> el.focus() );
                // reset the input value
                el.value = ""
                // do a default search with empty value
                this.search_fk_attr(attr,el);
            },

            cancel_edit_fk_value ( attr){
                this.$store[model_name].active_edit = "";
                this.$store[model_name].set_search_results();
            },

            search_fk_attr ( attr, el){
                const _this = this;
                let current_pks;
                if (isarray(this.model[attr])) {
                    current_pks = this.model[attr].map(x=>x.id);
                } else {
                    current_pks = this.model[attr] ?  [this.model[attr].id] : [];
                }
                const url = search_url.replace("__replace__",attr) + "?" + new URLSearchParams({q:el.value})

                GET(url,  json_response=true ).then(
                    resp => {
                        resp.json().then( data => {
                            for (var i in data["results"]){
                                const datum =  data["results"][i]
                                datum.selected =  current_pks.includes(datum.id)
                            }
                            _this.$store[model_name].set_search_results( data );
                        })
                    }
                )
            },

            toggle_fk_attr(attr,result){
                const _this = this;
                const el = htmx.find(`#${attr}_input${this.model.id}`);
                if (result.selected){
                    if (result.id && isarray(this.model[attr])) {
                        this.model[attr] = this.model[attr].filter(x=> x.id != result.id);
                    } else if (result.id){
                        this.model[attr] = undefined;
                    }
                    DELETE(result.url).then(x=>_this.update_model());
                } else {
                    if (isarray(this.model[attr])) {
                        this.model[attr] = [...this.model[attr], result];
                    } else {
                        this.model[attr] =  result;
                    }
                    POST(result.url, {}).then(x=>_this.update_model());
                }
                _this.cancel_edit_fk_value(attr);
            }
        }));
    });

})("{{model._meta.model_name}}")

