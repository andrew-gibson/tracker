import fetch_recipies from "fetch-recipies";

document.body.addEventListener('htmx:configRequest', (event) => {
  event.detail.headers['X-CSRFToken'] = fetch_recipies.csrf_token;
});
const setClipboard = (text) => {
    const type = "text/plain";
    const blob = new Blob([text], { type });
    const data = [new ClipboardItem({ [type]: blob })];
    navigator.clipboard.write(data);
};



const setup_rest_model_store = (model_name, fields)=> {



        Alpine.data(model_name, (model,update_url, search_url) => ({

            update_model () { 
                var _this = this;

                GETjson(update_url).then( json => _this.imodel= json);
            },


             async dateparse  (input, attr, id) {
                const resp = await GET(`{{url("core:dateparse")}}?q=${input.value}`)
                const text = await resp.text();
                const style = {};
                if (text) {
                    this.model[attr] = text;
                    input.style["border"] = "2px solid green";
                } else {
                    input.style["border"] = "2px solid red";
                }
             },

            async edit_value (attr,id) {
                this.$store[model_name].active_edit = this.model.id + attr;
                this.cancel_values[attr] = this.model[attr];
                if (["DateField", "DateTimeField"].includes(this.fields[attr])) {
                    const input = (await this.get_el(id))
                    input.value = "";
                    input.style["border"] = "";
                }
            },

            end_edit_value (attr) {
                this.send_model();
                this.$store[model_name].active_edit = "";
                this.cancel_values[attr] = "";
            },

            edit_fk_value (attr) {
                this.$store[model_name].active_edit = this.model.id + attr;
                this.$store[model_name].set_search_results();
                // tet ref to input element, can't use alpine refs for dynamically created elements
                const el = htmx.find(`#${attr}_input${this.model.id}`);
                // focus the input element
                this.$nextTick( ()=> el.focus() );
                // reset the input value
                el.value = ""
                // do a default search with empty value
                this.search_fk_attr(attr,el);
            },



        }));

    };

