import fetch_recipies from "fetch-recipies";
import "d3";
import 'lo-dash';


const inactive = {attr:"", d: {id:null}, search_results : []};
export const ui_state = mobx.makeAutoObservable({
    _active : inactive,
    get active (){
      return this._active;
    },
    set active (val){
       this._active = {search_results : [], ...val};
    },
    active_elements : [],
    models: await (await fetch_recipies.GET("/core/model_info/")).json(),
    active_model_info (){
       return this.models[this.active.d.__type__];
    },
    attr_type (){
       return this.active_model_info().fields[this.active.attr];
    },
    is_fk (type){
       type = type || this.attr_type()
       return  ["ManyToOneRel", "ManyToManyField", "ForeignKey"].includes(type);
    },
    make_id (active=null){
        active = active ? active : this.active;
        if (!active) {
            return "";
        }
        const id =  active.d.id ?  active.d.id : "__new__";
        return  `${active.d.__type__.replace(".","-")}-${id}-${active.attr}-`
    },
    ids (active=null){
        const id = this.make_id(active);
        if (!id){
            return {};
        }
        return {
            normal : `${id}normal`,
            insert : `${id}insert`,
            insert_input : `${id}input`,
            insert_label : `${id}input_label`,
        }
    },
    reset_active (e){
        this.active = inactive;
    },
    reset_ui(e) {
        this.active_elements = [];
        dispose_functions() ;
        document.dispatchEvent(new Event(e))
    },
});

window.reset_ui =   _.bind(ui_state.reset_ui, ui_state);
window.__uistate = ui_state;
const reset_active = _.bind(ui_state.reset_active, ui_state);
const handler = e => {
   if ("hx-replace-url" in e.target.attributes){
       window.reset_ui("HxReplaceURL");
   }
}
d3.select(document).on("htmx:beforeRequest",handler)
        
mobx.reaction(
    ()=>[ui_state.active.attr, ui_state.active.d.id],
    ()=>{
        d3.selectAll(".editor-insert").classed("d-none",true);
        d3.selectAll(".editor-normal").classed("d-none",false);
        if (ui_state.active.attr){
            const ids = ui_state.ids()
            d3.select(`#${ids.insert}`).classed("d-none",false);
            d3.select(`#${ids.normal}`).classed("d-none",true);
            _.delay(()=> {
                d3.select("#"+ids.insert_input).node().focus()
            },100);
            if (ui_state.is_fk()){
                q();
            }
    } 
});

//mobx.autorun(()=>{
//    if (ui_state.search_results.length){
//        d3.selectAll(".autocomplete-results").classed("d-none",true);
//        d3.select(`#${ui_state.id}`).select(".autocomplete-results").classed("d-none",false);
//    }
//});

const _dispose_functions = [];

export const dispose_functions = ()=>{
    _.each(_dispose_functions, f=>f());
};

export const autoRun = (func)=>{
    _dispose_functions.push(
      mobx.autorun(func)
    );
}

export const reaction = (data, func)=>{
    _dispose_functions.push(
      mobx.reaction(data,func)
    );
}


const isarray = Array.isArray;

const keyup_enter = func =>{
    return e => {
      if (e.key === "Enter" && !e.ctrlKey && !e.altKey) {
          func(e)
        }
      if (e.key === "Enter" && (e.ctrlKey || e.altKey)){
          e.target.value += "\n";
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

const force_list = (val)=>{
    if (isarray(val)){
        return val;
    }
    else if (val){
        return [val]
    }
    return [];
};

export const is_null = val =>{
    return force_list(val).length == 0
}

const observable_to_obj = model=>{
    const obj = {};
    const fields = ui_state.models[model.__type__].fields
    for (var x in fields){
        if (["ManyToOneRel", "ManyToManyField"].includes(fields[x]) ){
            const val =  (model[x] || []).map(x=>x.id);
            if (val.length) {
                obj[x] = val;
            }
        }  else if (fields[x] == "ForeignKey" ){
            const val = (model[x] || {}).id || "";
            if (val){
                obj[x] = val;
            }
        } else if (x in model){
            obj[x] = model[x] || "";
        }
    }
    return obj;
}

const send_model = async model =>{
    const obj = observable_to_obj(model);
    let f ;
    let url;
    if (obj.id) {
        f = fetch_recipies.PUT;
        url = ui_state.models[model.__type__].rest_pk.replace("__pk__",model.id);
    } else {
        f = fetch_recipies.POST;
        url = ui_state.models[model.__type__].rest;
    }
    const resp = await f(url, 
        new URLSearchParams(obj).toString(), 
        true );
    const data = await resp.json();
    Object.assign(model,data);
};

const q = async (e)=>{
    if (ui_state.active && ui_state.is_fk()){
        let current_pks;
        const { attr ,  d } = ui_state.active;
        const q = _.isUndefined(e) ? "" :  e.target.value;
        if (isarray(d[attr])) {
            current_pks = _.map(d[attr],x=>x.id);
        } else {
            current_pks = d[attr] ?  [d[attr].id] : [];
        }
        const url = ui_state.models[d.__type__]
                                .search_relation
                                .replace("__pk__",d.id)
                                .replace("__attr__",attr)   + "?" + new URLSearchParams({q});

        const resp = await fetch_recipies.GET(url, true );
        const data = await resp.json();
        ui_state.active.search_results = _.chain(data.results)
                                  .each(_d=>{
                                     _d.selected =  current_pks.includes(_d.id)
                                  })
                                  .sortBy("name")
                                  .sortBy(_d=>{
                                     return _d.selected ? 0 : 1
                                  }) 
                                  .value();
    }
};

const debounced_q = _.debounce(q,250);

const toggle_fk_attr = async (result) => {
    const { attr ,  d } = ui_state.active;
    const model_info =  ui_state.active_model_info();

    if (result.selected){
        if (result.id && isarray(d[attr])) {
            d[attr] = d[attr].filter(x=> x.id != result.id);
        } else if (result.id){
            d[attr] = undefined;
        }
        await fetch_recipies.DELETE(result.url);
    } else {
        if (isarray(d[attr])) {
            d[attr] = [...d[attr], result];
        } else {
            d[attr] =  result;
        }
        await fetch_recipies.POST(result.url, {},true);
    }
    const data = await fetch_recipies.GETjson(model_info.rest_pk.replace("__pk__",d.id));
    d[attr] = data[attr];
};

d3.selection.prototype.styles = function(attrs){
    for ( var key in attrs ){
      this.node().style[key]  = attrs[key];
    }
    return this;
}
d3.selection.prototype.attrs = function(attrs){
    for ( var key in attrs ){
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

d3.selection.prototype.last = function() {
  const last = this.size() - 1;
  return d3.select(this.nodes()[last]);
}

export const make_cancel_button = function(selection){
    selection
            .append("button")
            .classed("btn-close ms-2",true)
            .attr("aria-label","Close")
            .on("click", reset_active)
    };

export const make_right_dropdown = function(selection, call){
    selection
        .append("div")
            .classed("dropdown d-flex justify-content-end",true)
            .append("button")
                .classed("btn btn-light m-0 p-1",true)
                .attrs({
                 "type": "button",
                 "data-bs-toggle" : "dropdown",
                "aria-expanded"  : "false",
                })
                .style("font-size", "0.6em")
                .html("☰")
            .select_parent()
            .append("ul")
                .classed("dropdown-menu",true)
                .call(call)
}
export const create_button = function(selection,make_observable_data, attr="",title="" ,options){

    const ids = ui_state.ids({attr,d:make_observable_data() })
    const {on_change} = options;

    const sel = selection
        .append("div")
        .classed(`mb-1`, true)

    const insert_mode = sel
        .append("div")
        .attr("id",ids.insert)
        .classed(`editor-insert d-none ${attr}-row`,true)
        .append("div")
        .classed(`justify-content-between d-flex align-items-center`,true)
        .append("input")
        .classed("form-control ps-2 pe-0 w-100",true)
        .attrs({
            "id": ids.insert_input,
            "name" : attr,
            "data-1p-ignore" : "true",
            "placeholder" : title,
        })
        .on("keyup",function(e) {
            keyup_esc(reset_active)(e)
            keyup_enter(e=>{
                ui_state.active.d[attr] =  e.target.value;
                send_model(ui_state.active.d);
                reset_active(e)
                this.value = "";
                if (on_change){
                    _.delay(ui_state.reset_ui, 100, on_change)
                }
            })(e)
        })
        .select_parent()
        .call(make_cancel_button)

    sel
        .append("div")
        .classed(`editor-normal ${attr}-row`,true)
        .attr("id",ids.normal)
        .append("button")
        .classed("btn btn-sm btn-light p-1 m-1",true)
        .on("click", () => {
            d3.select(`#${ids.insert_input}`).node().value = "";
            ui_state.active = {
                attr, 
                d: make_observable_data()}
        })
        .html(title)
};

export const inplace_edit = function(selection,
                                    observable_data, 
                                    attr="",
                                    title="" , 
                                    options={} ){

    const {btn_class="btn-light", on_change=null,input_class="",display_attr=attr} = options;
    const ids = ui_state.ids({attr,d:observable_data})

    const insert_mode = selection
        .append("div")
        .attr("id",ids.insert)
        .classed(`editor-insert d-none ${attr}-row justify-content-between d-flex align-items-center`,true)
        .append("input")
        .classed(`form-control ps-2 pe-0 `,true)
        .attrs({
            "id": ids.insert_input,
            "name" : attr,
            "data-1p-ignore" : "true",
            "placeholder" : title,
        })
        .on("keyup",e => {
            keyup_esc(reset_active)(e)
            keyup_enter(e=>{
                observable_data[attr] = e.target.value;
                send_model(observable_data);
                reset_active(e)
                if (on_change){
                    _.delay(ui_state.reset_ui, 100, on_change)
                }
            })(e)
        })
        .call(selecion=>{
            autoRun(()=>selecion.node().value = observable_data[attr])
        })
        .select_parent()
        .call(make_cancel_button)

    selection
        .append("div")
        .classed(`editor-normal ${attr}-row`,true)
        .attr("id",ids.normal)
        .append("button")
        .classed(`btn ${btn_class} p-1 m-1`,true)
        .on("click", () => ui_state.active = {attr, d:observable_data})
        .call(selecion=>{
            autoRun(()=>selecion.html(observable_data[display_attr] || "+"))
        });

}

export const append_edit_attr = function(selection,observable_data, ...args ){
    const type = ui_state.models[observable_data.__type__].fields[args[0]]
    if (ui_state.is_fk(type)){
        append_edit_fk(selection,observable_data, ...args )
    }  else {
        append_edit_local_attr(selection,observable_data,  ...args )
    }
}

export const append_edit_local_attr = function(selection,observable_data, attr="",title="",options={on_change:null}  ){
    const {on_change} = options;
    const type = ui_state.models[observable_data.__type__].fields[attr]
    const ids = ui_state.ids({attr,d:observable_data})

    const sel = selection
        .append("div")
        .classed(`mb-1`, true)

    const insert_mode = sel
        .append("div")
        .attr("id",ids.insert)
        .classed(`editor-insert d-none ${attr}-row`,true)

    sel
        .append("div")
        .classed(`editor-normal ${attr}-row`,true)
        .attr("id",ids.normal)
        .append("div")
        .classed(`justify-content-between d-flex align-items-center`,true)
        .styles({
            "max-width" : "100%",
            "font-size" : "0.8em",
        })
        .call(function(selection){
            const normal_mode = selection
            if (type == "BooleanField"){
                normal_mode
                    .append("span")
                    .classed("me-2",true)
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
                        .on("change",e=>{
                            observable_data[attr] = e.target.checked;
                            send_model(observable_data);
                            if (on_change){
                                _.delay(ui_state.reset_ui, 100, on_change)
                            }
                        })
                        .call(selecion=>{
                            autoRun(()=>selecion.node().checked=observable_data[attr] )
                        });

            } else if (type == "DateField"){
                normal_mode
                    .append("div")
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1",true)
                    .on("click",()=> ui_state.active = {attr, d : observable_data})
                    .html(title)
                .select_parent()
                .select_parent()
                    .append("div")
                    .classed("w-50 ",true)
                    .append("input")
                    .attr("type","date")
                    .classed("form-control ps-2 pe-0",true)
                    .call(selecion=>{
                        autoRun(()=>selecion.node().value = observable_data[attr] )
                    })


            } else if (type == "CharField"){
                normal_mode
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1",true)
                    .on("click",()=> ui_state.active = {attr, d : observable_data})
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
                    .classed("form-control ps-2 pe-0",true)
                    .attrs({
                        "id": ids.insert_input,
                        "name" : attr,
                        "data-1p-ignore" : "true",
                    })
                    .on("keyup",e => {
                        keyup_esc(reset_active)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            if (on_change){
                                _.delay(ui_state.reset_ui, 100, on_change)
                            }
                            reset_active(e)
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
                    .on("click", ()=> ui_state.active = {attr, d : observable_data})
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
                    .attr("rows", 5)
                    .attr("name", attr)
                    .on("keyup",e => {
                        keyup_esc(reset_active)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            reset_active(e)
                            if (on_change){
                                _.delay(ui_state.reset_ui, 100, on_change)
                            }
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
                        .on("click",()=>{
                            const input = d3.select(`#${ids.insert_input}`).node();
                            observable_data[attr] = input.value;
                            send_model(observable_data);
                            if (on_change){
                                _.delay(ui_state.reset_ui, 100, on_change)
                            }
                            reset_active()
                        })
                    .select_parent()
                        .append("button")
                        .classed("btn btn-sm btn-danger" ,true)
                        .html("Cancel")
                        .on("click", reset_active)
            }
        })
}

export const append_edit_fk = function(selection,
                                       observable_data, 
                                       attr="",
                                       title="",
                                       options={} ){

    const {on_change=null, read_only=false,name_attr="name"} = options;
    const ids = ui_state.ids({attr,d:observable_data})
    const sel = selection
        .append("div")
        .classed(`mb-1 `, true)

    if (!read_only) {
        const insert_mode = sel
            .append("div")
            .attr("id",ids.insert)
            .classed(`editor-insert ${attr}-row d-none pt-2`,true)
            .style("width","100%")
            .style("background","white")
            .append("div")
            .classed("input-group input-group-sm d-flex align-items-center pb-2",true)
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
                keyup_esc(reset_active)(e);
                debounced_q(e);
            } )
            .select_parent()
            .call(make_cancel_button)
            .select_parent()
            .append("div")
            .styles({
                "overflow-x": "scroll", 
                "scrollbar-width":"none",
                "max-width": "100%",
                "padding-bottom": "10px",
                "font-size" : "0.8em",
            })
            .append("ul")
            .classed("list-group list-group-horizontal border-top border-bottom",true)
            .call( selection=>{
                reaction( ()=> ui_state.active.search_results.length,
                    ()=>{
                    if (ui_state.active.d.id == observable_data.id && ui_state.active.attr == attr){
                        selection
                            .selectAll("li")
                            .data(ui_state.active.search_results, d=> d.id )
                            .join("li")
                            .classed("list-group-item d-flex p-1 me-1 border-0  align-items-stretch",true)
                            .selectAll("span.result-container")
                            .data(d=>[d])
                            .join("span")
                            .classed("result-container rounded p-1", true)
                            .style("border", d =>  `2px solid ${d.selected ? ui_state.models[d.__type__].hex : "#fff"}`)
                            .style("background-color", d=> ui_state.models[d.__type__].rgba)
                            .selectAll("button")
                            .data(d=>[d])
                            .join("button")
                            .on("click", (e,d)=>{
                                toggle_fk_attr(d);
                                ui_state.reset_active();
                                if (on_change){
                                    _.delay(ui_state.reset_ui, 100, on_change)
                                }
                            })
                            .style( "font-size" , "1em")
                            .classed("btn p-1 fw-bold ",true)
                            .call(selection=>{
                                selection
                                    .selectAll("span.name")
                                    .data(d=>[d])
                                    .join("span")
                                    .classed("name rounded-1 text-nowrap ",true)
                                    .html(d=>d.name)
                                selection
                                    .selectAll("span.badge")
                                    .data(d=>[d])
                                    .join("span")
                                    .classed("badge bg-success ms-1",true)
                                    .classed("d-none", d=>!d.new )
                                    .html("New")
                            })
                    }
                })
            })

    } 

    sel
        .append("div")
        .classed(`editor-normal ${attr}-row`,true)
        .attr("id",ids.normal)
        .append("div")
        .classed("justify-content-between d-flex align-items-center",true)
        .styles({
            "overflow-x" : "scroll",
            "scrollbar-width":"none",
            "max-width" : "100%",
            "font-size" : "0.8em",
        })
        .call(selection=>{
            if (read_only){
                selection
                .append("span")
                .classed("mb-1",true)
                .styles({
                    "font-weight" : "400",
                    "font-size" : "1rem",
                    "line-height" : "1.5",
                    "padding": ".375rem .75rem",
                })
                .html(title)
            } else {
                selection
                .append("button")
                .attr("type","button")
                .classed("btn btn-link mb-1",true)
                .on("click", ( e, d ) => ui_state.active = {attr, d:observable_data})
                .html(title)

            }
        })
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
                    .classed("list-group-item d-flex p-1 me-1 bg-opacity-10 border-1 w-100 fw-bold text-nowrap ",true)
                    .style("background-color",dd=>  ui_state.models[dd.__type__].rgba)
                    .style("border-color",dd=>  ui_state.models[dd.__type__].hex)
                    .html(d=>d[name_attr])
            })
        });
};


/*
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
*/

