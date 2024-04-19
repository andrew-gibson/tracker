d3.selection.prototype.styles = function(attrs){
    for ( key in attrs ){
      this.node().style[key]  = attrs[key];
    }
    return this;
}
d3.selection.prototype.attrs = function(attrs){
    for ( key in attrs ){
      this.node().setAttribute(key, attrs[key]);
    }
    return this;
}
d3.selection.prototype.setup_htmx = function(){
    htmx.process(this.node());
    return this;
}
d3.selection.prototype.select_parent = function(){
   return d3.select(this.node().parentElement);
}


const csrf_token =  '{{ csrf_token }}';
const headers =   {  'X-CSRFToken' : csrf_token,  'Content-Type': 'application/json' };
document.body.addEventListener('htmx:configRequest', (event) => {
  event.detail.headers['X-CSRFToken'] = csrf_token;
});
const GET = async (url, json_response = false,) => {
    return await fetch( url, {headers : {'json-response' : json_response.toString(),...headers}});
};
const GETjson =  async (url,json_response = true) => {
    return await (await GET(url)).json();
};               
const PUT = async (url, body, json_response = false, ) => {
    const headers = {
        'X-CSRFToken' : csrf_token, 
        'json-response' : json_response.toString(),
       'Content-Type': 'application/x-www-form-urlencoded'
    };
    return await fetch( url, {method: "PUT",headers, body});
};
const POST = async (url, body, json_response = false, ) => {
    const headers = {
        'X-CSRFToken' : csrf_token, 
        'json-response' : json_response.toString(),
        'Content-Type': 'application/x-www-form-urlencoded'
    };
    return await fetch( url, {method: "POST",headers, body});
};
const DELETE = async (url) => {
    return await fetch( url, {method: "DELETE",headers  });
};

const keyup_enter = func =>{
    return e => {
      if (e.key === "Enter") {
          func(e)
        }
    }
}

const keyup_esc = func =>{
    return e => {
      if (e.key === "Escape") {
          func(e)
        }
    }
}


const setClipboard = (text) => {
    const type = "text/plain";
    const blob = new Blob([text], { type });
    const data = [new ClipboardItem({ [type]: blob })];
    navigator.clipboard.write(data);
};

const dispose_functions = [];
const autoRun = (func)=>{
    dispose_functions.push(
      mobx.autorun(func)
    );
}

const state = mobx.makeAutoObservable({
    id : null,
    search_results : [],
    models: {{models()}},
    stores : new Map(),
    make_id (d,attr){
        return  `${d.__type__.replace(".","-")}-${d.id}-${attr}-`
    },
    ids (id=null){
        id = id ? id : this.id;
        if (id === null){
            return {}
        }
        return {
            normal : `${id}normal`,
            insert : `${id}insert`,
            insert_input : `${id}input`,
            insert_label : `${id}input_label`,
        }
    },
    cancel_edit (e){
        this.id = null;
    }
})

const send_model = model =>{
    const send_data = {};
    const fields = state.models[model.__type__].fields
    const update_url = state.models[model.__type__].rest_pk.replace("__pk__",model.id);
    for (var x in fields){
        if (["ManyToOneRel", "ManyToManyField"].includes(fields[x]) ){
            val =  (model[x] || []).map(x=>x.id);
            if (val.length) {
                send_data[x] = val;
            }
        }  else if (fields[x] == "ForeignKey" ){
            val = (model[x] || {}).id || "";
            if (val){
                send_data[x] = val;
            }
        } else if (x in model){
            send_data[x] = model[x] || "";
        }
    }
    PUT(update_url, 
        new URLSearchParams(send_data).toString(), 
        json_response=true ).then(
            resp => {
                resp.json().then( data => {
                    Object.assign(model,data);
                });
            }
        );
};

const force_list = (val)=>{
    const isarray = Array.isArray;
    if (isarray(val)){
        return val;
    }
    else if (val){
        return [val]
    }
    return [];
};

mobx.autorun(()=>{
    d3.selectAll(".editor-insert").classed("d-none",true);
    d3.selectAll(".editor-normal").classed("d-none",false);
    if (state.id){
        const ids = state.ids()
        d3.select(`#${ids.insert}`).classed("d-none",false);
        d3.select(`#${ids.normal}`).classed("d-none",true);
        _.delay(()=> d3.select("#"+ids.insert_input).node().focus(),100);
    } 
});
mobx.autorun(()=>{
    if (state.search_results){
        d3.selectAll(".autocomplete-results").classed("d-none",true);
        d3.select(`#${state.id}`).select(".autocomplete-results").classed("d-none",false);
    }
});

const make_cancel_button = function(selection){
    selection
        .append("button")
        .classed("btn-close ms-2",true)
        .attr("aria-label","Close")
        .on("click", (e)=>state.cancel_edit(e))
};


const append_edit_attr = function(selection,observable_data, attr="",title="" ){
    const d = selection.data()[0]
    const type = state.models[d.__type__].fields[attr]
    const core_id = state.make_id(d,attr)
    const ids = state.ids(core_id)

    const sel = selection
        .append("div")
        .classed("mb-1", true)

    insert_mode = sel
        .append("div")
        .attr("id",ids.insert)
        .classed("editor-insert d-none",true)

    sel
        .append("div")
        .classed("editor-normal",true)
        .attr("id",ids.normal)
        .append("div")
        .classed("justify-content-between d-flex align-items-center",true)
        .styles({
            "max-width" : "100%",
            "font-size" : "0.8em",
        })
        .call(function(selection){
            const normal_mode = selection
            if (type == "BooleanField"){
                normal_mode
                    .append("span")
                    .classed("mb-1",true)
                    .style("padding", ".375rem .75rem")
                    .html(title)
                .select_parent()
                .append("div")
                    .classed("form-check form-switch",true)
                        .append("input")
                        .attr("type","checkbox")
                        .attr("role","switch")
                        .attr("role",attr)
                        .style("font-size","1.5em")
                        .classed("form-check-input",true)
                        .on("change",keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                        }))
                        .call(selecion=>{
                            autoRun(()=>selecion.attr("value",observable_data[attr] ))
                        });

            } else if (type == "DateField"){

            } else if (type == "CharField"){
                normal_mode
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1",true)
                    .on("click",event=> state.id = core_id)
                    .html(title)
                .select_parent()
                    .append("div")
                    .classed("me-1",true)
                    .call(selecion=>{
                        autoRun(()=>selecion.html(observable_data[attr] ))
                    })

                insert_mode
                    .append("div")
                    .classed("d-flex align-items-center",true)
                    .append("span")
                    .classed("input-group-text w-25",true)
                    .attr("id", ids.insert_label)
                    .html(title)
                .select_parent()
                    .append("div")
                    .classed("w-75 d-flex align-items-center",true)
                    .append("input")
                    .classed("form-control ps-0 pe-0",true)
                    .attr("id",ids.insert_input)
                    .attr("name", attr)
                    .on("keyup",e => {
                        keyup_esc(state.cancel_edit)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            state.cancel_edit(e)
                        })(e)
                    })
                    .call(selection =>{
                        autoRun(()=>selection.attr("value",observable_data[attr] ))
                    })
                .select_parent()
                .call(make_cancel_button)



            } else if (type == "TextField"){
                normal_mode
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1",true)
                    .on("click",event=> state.id = core_id)
                    .html(title)
                .select_parent()
                    .append("div")
                    .classed("me-1",true)
                    .call(selecion=>{
                        autoRun(()=>selecion.html(observable_data[attr] ))
                    })

                insert_mode
                    .append("div")
                    .classed("align-items-center border p-1 w-100",true)
                    .append("span")
                    .classed("input-group-text w-100",true)
                    .attr("id", ids.insert_label)
                    .html(title)
                .select_parent()
                    .append("textarea")
                    .classed("form-control mt-1",true)
                    .attr("id",ids.insert_input)
                    .attr("name", attr)
                    .on("keyup",e => {
                        keyup_esc(e=> state.id = null)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            state.cancel_edit(e)
                        })(e)
                    })
                    .call(selection =>{
                        autoRun(()=>{
                          selection.html(observable_data[attr])
                        } )
                    })
                .select_parent()
                    .append("div")
                    .classed("btn-group pt-2",true)
                        .append("button")
                        .classed("btn btn-sm btn-success" ,true)
                        .html("Save")
                        .on("click",()=>true)
                    .select_parent()
                        .append("button")
                        .classed("btn btn-sm btn-danger" ,true)
                        .html("Cancel")
                        .on("click", e=> state.id = null)
            }
        })
}

const append_edit_fk = function(selection,observable_data, attr="",title="" ){

    const d = selection.data()[0]
    const type = state.models[d.__type__].fields[attr]
    const core_id = state.make_id(d,attr)
    const ids = state.ids(core_id)
    const debounced_q = _.debounce((e)=>{
       // write the code to search

    },wait=250);
    const sel = selection
        .append("div")
        .classed("mb-1", true)

    insert_mode = sel
        .append("div")
        .attr("id",ids.insert)
        .classed("editor-insert d-none border p-2",true)
        .style("width","100%")
        .append("div")
        .classed("input-group input-group-sm d-flex align-items-center ",true)
        .append("span")
        .attr("id",ids.insert_label)
        .html(title)
        .select_parent()
        .append("input")
        .classed("form-control",true)
        .attrs({
            "type":"text",
            "id" :  ids.insert_input,
            "area-describedby" : ids.insert_label,
            "autocomplete" : "off",
            "data-1p-ignore" : "true",
            "name" : "name"
        })
        .on("keyup",e =>{
            keyup_esc(e=> state.id = null)(e);
            debounced_q(e);
        } )
        .select_parent()
        .call(make_cancel_button)
        .select_parent()
        .append("div")
        .styles({
            "overflow-x": "scroll", 
            "max-width": "100%",
            "padding-bottom": "10px",
            "font-size" : "0.8em",
        })
        .append("ul")
        .classed("list-group list-group-horizontal pt-2 ",true)
        .call( selection=>{
            autoRun( ()=>{
                state.search_results.length
                if (state.id == core_id ){

                    selection
                        .selectAll("li")
                        .data(state.search_results, d=>  d.id )
                        .join("li")
                        .classed("list-group-item d-flex p-1 me-1 border-0  align-items-stretch",true)
                        .selectAll("span.result-container")
                        .data(d=>[d])
                        .join("span")
                        .classed("result-container", true)
                        .style("border", d=> d.selected ? `1px solid ${state.models[d.__type__].hex}` : "")
                        .style("background-color", d=> state.models[d.__type__].rbga)
                        .selectAll("button")
                        .data(d=>[d])
                        .join("button")
                        .classed("btn p-2",true)
                        .call(selection=>{
                            selection
                                .selectAll("span.name")
                                .data(d=>[d])
                                .join("span")
                                .classed("name",true)
                                .html(d=>d.name)
                            selection
                                .selectAll("span.badge")
                                .data(d=>[d])
                                .join("span")
                                .classed("badge bg-success ms-1",true)
                                .style("display", d=> d.selected ? "" : "d-none")
                                .html("New")
                        })

                }
            })
        })
                


    sel
        .append("div")
        .classed("editor-normal",true)
        .attr("id",ids.normal)
        .append("div")
        .classed("justify-content-between d-flex align-items-center",true)
        .styles({
            "overflow-x" : "scroll",
            "scrollbar-width":"none",
            "max-width" : "100%",
            "font-size" : "0.8em",
        })
        .append("button")
        .attr("type","button")
        .classed("btn btn-link mb-1",true)
        .on("click",event=> state.id = core_id)
        .html(title)
        .call(function(args){
        })
        .select_parent()
        .append("li")
        .classed("list-group list-group-horizontal d-flex align-items-center",true)
        .styles({
            "overflow-x": "scroll", 
            "max-width": "80%",
            "scrollbar-width":"none",
        })
        .call(selection=>{
            autoRun(()=>{
                selection
                    .selectAll("li")
                    .data(force_list(observable_data[attr]))
                    .join("li")
                    .classed("list-group-item d-flex p-1 me-1 bg-opacity-10 border-1 w-100 fw-bold",true)
                    .style("background-color",dd=>{
                        return state.models[dd.__type__].rbga;
                    })
                    .style("border-color",dd=>{
                        return state.models[dd.__type__].hex;
                    })
                    .html(d=>d.name)
            })
        });
};




const setup_rest_model_store = (model_name, fields)=> {

        const isarray = Array.isArray;


        Alpine.data(model_name, (model,update_url, search_url) => ({

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
                // get ref to input element, can't use alpine refs for dynamically created elements
                const el = htmx.find(`#${attr}_input${this.model.id}`);
                // focus the input element
                this.$nextTick( ()=> el.focus() );
                // reset the input value
                el.value = ""
                // do a default search with empty value
                this.search_fk_attr(attr,el);
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

    };
{% block scripts %}{% endblock %}

