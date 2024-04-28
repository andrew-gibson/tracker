import fetch_recipies from "fetch-recipies";
import "d3";
import 'lo-dash';

export const ui_state = mobx.makeAutoObservable({
    active : null,
    search_results : [],
    active_elements : [],
    models: await (await fetch_recipies.GET("/core/model_info/")).json(),
    active_model_info (){
       return this.models[this.active.d.__type__];
    },
    attr_type (){
       return this.active_model_info().fields[this.active.attr];
    },
    is_fk (){
       return  ["ManyToOneRel", "ManyToManyField", "ForeignKey"].includes(this.attr_type());
    },
    make_id (active=null){
        active = active ? active : this.active;
        if (!active) {
            return "";
        }
        return  `${active.d.__type__.replace(".","-")}-${active.d.id}-${active.attr}-`
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
    cancel_edit (e){
        this.active = null;
    },
    reset_ui(e) {
        this.active_elements = [];
        dispose_functions() ;
        document.dispatchEvent(new Event(e))
    },
});

window.reset_ui =   _.bind(ui_state.reset_ui, ui_state);
const handler = e => {
   if ("hx-replace-url" in e.target.attributes){
       window.reset_ui("HxReplaceURL");
   }
}
d3.select(document).on("htmx:beforeRequest",handler)
        
mobx.autorun(()=>{
    d3.selectAll(".editor-insert").classed("d-none",true);
    d3.selectAll(".editor-normal").classed("d-none",false);
    if (ui_state.active){
        ui_state.search_results = [];
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

mobx.autorun(()=>{
    if (ui_state.search_results.length){
        d3.selectAll(".autocomplete-results").classed("d-none",true);
        d3.select(`#${ui_state.id}`).select(".autocomplete-results").classed("d-none",false);
    }
});

const _dispose_functions = [];

export const dispose_functions = ()=>{
    _.each(_dispose_functions, f=>f());
};

export const autoRun = (func)=>{
    _dispose_functions.push(
      mobx.autorun(func)
    );
}

const isarray = Array.isArray;

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

const force_list = (val)=>{
    if (isarray(val)){
        return val;
    }
    else if (val){
        return [val]
    }
    return [];
};

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
    const update_url = ui_state.models[model.__type__].rest_pk.replace("__pk__",model.id);
    const obj = observable_to_obj(model);
    const resp = await fetch_recipies.PUT(update_url, 
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
        ui_state.search_results = _.chain(data.results)
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

const toggle_fk_attr = async (result,model) => {
    const { attr ,  d } = ui_state.active;
    const model_info =  ui_state.active_model_info();

    if (result.selected){
        if (result.id && isarray(model[attr])) {
            model[attr] = model[attr].filter(x=> x.id != result.id);
        } else if (result.id){
            model[attr] = undefined;
        }
        await fetch_recipies.DELETE(result.url);
    } else {
        if (isarray(model[attr])) {
            model[attr] = [...model[attr], result];
        } else {
            model[attr] =  result;
        }
        await fetch_recipies.POST(result.url, {},true);
    }
    ui_state.cancel_edit();
    const data = await fetch_recipies.GETjson(model_info.rest_pk.replace("__pk__",model.id));
    Object.assign(model,data);
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

const make_cancel_button = function(selection){
    selection
            .append("button")
            .classed("btn-close ms-2",true)
            .attr("aria-label","Close")
            .on("click", (e)=>ui_state.cancel_edit(e))
    };

export const make_right_dropdown = function(selection, call){
    selection
        .append("div")
            .classed("dropdown d-flex justify-content-end",true)
            .append("button")
                .classed("btn btn-light m-1 p-1",true)
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

export const append_edit_attr = function(selection,observable_data, attr="",title="" ){
    const d = selection.data()[0]
    const type = ui_state.models[d.__type__].fields[attr]
    const ids = ui_state.ids({attr,d})

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
                        .on("change",e=>{
                            observable_data[attr] = e.target.checked;
                            send_model(observable_data);
                        })
                        .call(selecion=>{
                            autoRun(()=>selecion.node().checked=observable_data[attr] )
                        });

            } else if (type == "DateField"){
                normal_mode
                    .append("div")
                    .classed("d-flex w-25",true)
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1 w-25",true)
                    .on("click",( event, d )=> ui_state.active = {attr, d})
                    .html(title)
                .select_parent()
                .select_parent()
                    .append("div")
                    .classed("w-50 ",true)
                    .append("input")
                    .attr("type","date")
                    .classed("form-control ps-0 pe-0",true)
                    .call(selecion=>{
                        autoRun(()=>selecion.node().value = observable_data[attr] )
                    })


            } else if (type == "CharField"){
                normal_mode
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1",true)
                    .on("click",( event, d )=> ui_state.active = {attr, d})
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
                        keyup_esc(ui_state.cancel_edit)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            ui_state.cancel_edit(e)
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
                    .on("click", ( event, d )=> ui_state.active = {attr, d})
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
                        keyup_esc(ui_state.cancel_edit)(e)
                        keyup_enter(e=>{
                            observable_data[attr] = e.target.value;
                            send_model(observable_data);
                            ui_state.cancel_edit(e)
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
                            ui_state.cancel_edit()
                        })
                    .select_parent()
                        .append("button")
                        .classed("btn btn-sm btn-danger" ,true)
                        .html("Cancel")
                        .on("click",e=> ui_state.cancel_edit())
            }
        })
}

export const append_edit_fk = function(selection,observable_data, attr="",title="" ){

    const d = selection.data()[0]
    const ids = ui_state.ids({attr,d})
    const sel = selection
        .append("div")
        .classed(`mb-1 `, true)

    const insert_mode = sel
        .append("div")
        .attr("id",ids.insert)
        .classed(`editor-insert ${attr}-row d-none border p-2`,true)
        .style("width","100%")
        .style("background","white")
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
            keyup_esc(e=> ui_state.active = null)(e);
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
        .classed("list-group list-group-horizontal pt-2 ",true)
        .call( selection=>{
            autoRun( ()=>{
                ui_state.search_results.length
                if (ui_state.active && ui_state.active.attr == attr ){
                    selection
                        .selectAll("li")
                        .data(ui_state.search_results, d=>  d.id )
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
                           toggle_fk_attr(d,observable_data);
                        })
                        .style( "font-size" , "1em")
                        .classed("btn p-1 fw-bold ",true)
                        .call(selection=>{
                            selection
                                .selectAll("span.name")
                                .data(d=>[d])
                                .join("span")
                                .classed("name rounded-1",true)
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
        .append("button")
        .attr("type","button")
        .classed("btn btn-link mb-1",true)
        .on("click",( event, d )=> ui_state.active = {attr, d})
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
                        return ui_state.models[dd.__type__].rgba;
                    })
                    .style("border-color",dd=>{
                        return ui_state.models[dd.__type__].hex;
                    })
                    .html(d=>d.name)
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

