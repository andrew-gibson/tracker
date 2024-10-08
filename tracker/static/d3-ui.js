import "d3";
import 'lo-dash';

const headers =  {  'X-CSRFToken' : csrf_token,  'Content-Type': 'application/json' };
export const fetch_recipies = {
    csrf_token,
    headers,
    GET : async (url, json_response = false,) => {
        return await fetch( url, {headers : {'json-response' : json_response.toString(),...headers}});
    },
    GETjson :  async (url,json_response = true) => {
        return await (await fetch_recipies.GET(url)).json();
    },               
    PUT : async (url, body, json_response = false, ) => {
        const headers = {
            'X-CSRFToken' : csrf_token, 
            'json-response' : json_response.toString(),
           'Content-Type': 'application/x-www-form-urlencoded'
        };
        return await fetch( url, {method: "PUT",headers, body});
    },
    POST : async (url, body, json_response = false, ) => {
        const headers = {
            'X-CSRFToken' : csrf_token, 
            'json-response' : json_response.toString(),
            'Content-Type': 'application/x-www-form-urlencoded'
        };
        return await fetch( url, {method: "POST",headers, body});
    },
     DELETE : async (url) => {
        return await fetch( url, {method: "DELETE",headers  });
    }
};

export default fetch_recipies;
window.__fetch =  fetch_recipies;

const models = await fetch_recipies.GETjson("/project/model_info/");

const prep_data = observable_data =>{
    const type = ui_state.models[observable_data.__type__]
    if (!observable_data.id){
        observable_data.id = "new" + _.random(10000000000000000000)
        if (!observable_data.__perms__){
            observable_data.__perms__ = {POST : type.POST}
        } else {
            observable_data.__perms__["POST"]= type.POST
        }
    }
}


class UIState {
    models = models
    _attr = ""
    _d = {id:null}
    _search_results = []
    _user = {}

    constructor(){
        mobx.makeAutoObservable(this,{deep:true })
        this.refresh_limit = 2160000;  // time limit after which, refresh data store by default
    }

    set user (val){
      return this._user = val;
    }

    get user (){
      return this._user;
    }

    get attr (){
      return this._attr;
    }

    set attr(val){
        this._attr = val
    }

    get d (){
      return this._d;
    }

    set d(val){
        this._d = val
    }

    get search_results (){
      return this._search_results;
    }

    set search_results (val){
      return this._search_results = val;
    }

    get active_model_info (){
       return this.models[this._d.__type__];
    }

    get attr_type (){
       return this.active_model_info.fields[this.attr];
    }

    is_fk (type){
       type = type || this.attr_type
       return  ["ManyToOneRel", "ManyToManyField", "ForeignKey","OneToOneRel"].includes(type);
    }

    make_id (__type__, id, attr){
        return  `${__type__.replace(".","-")}-${id}-${attr}-`
    }

    ids (active=null){
        var id
        if (active) {
            id = this.make_id(active.d.__type__, active.d.id , active.attr);
        } else if (this.attr){
            id = this.make_id(this.d.__type__, this.d.id , this.attr);
        }
        return {
            normal : `${id}normal`,
            insert : `${id}insert`,
            insert_input : `${id}input`,
            insert_label : `${id}input_label`,
        }
    }
    async refresh_model_store (model,data=null){
      if (!data){
         const filters = _.omitBy(this.models[model].filters, _.isUndefined);
         const url = this.models[model].main;
         const get_params = `?f=${btoa(JSON.stringify({filters}))}`;
         const resp = await fetch_recipies.GET(url+get_params);
         if (resp.status == 200) {
             const server_data = await resp.json();
             if ("errors" in server_data) {
                 // TODO deal with save error

             } else {
                 //update the data
                 this.models[model].data = server_data;
             }
         }
      } else {
          this.models[model].data = data;
     }
     this.models[model].refresh_time = Date.now();
      return this.models[model].data;
    }
    update_store(obj){
        const store =  this.models[obj.__type__].data;
        var index = _.findIndex(store, d=>d.id == obj.id);
        if (index!=-1){
            _.assign(store[index],obj);
        } else{
            this.models[obj.__type__].data = [...store, obj];
            index = this.models[obj.__type__].data.length - 1
        }
        // have to use full path to ensure mobX sees the change
        this.models[obj.__type__].refresh_time = Date.now();
        return this.models[obj.__type__].data[index];
    }
    async get_store(model){
        if (this.models[model].data.length == 0) {
            await this.refresh_model_store(model)
        }
        if (this.models[model].refresh_time > Date.now() + this.refresh_limit){
            await this.refresh_model_store(model)
        }
        return this.models[model].data
    }
    reset_active (){
        const temp_new_state = new UIState()
        this.search_results =  temp_new_state.search_results
        this.attr =  temp_new_state.attr
        this.d =  temp_new_state.d
    }
    signal(e){
        if (e){
            if (!_.isArray(e)){
                e = [e]
            }
            _.each(e, _e=>{
                if (_.isFunction(_e)){
                    _e();
                } else {
                    document.dispatchEvent(new Event(_e));
                }
            })
        }
    }
    reset_ui(e) {
        card_state.reset();
        _dispose_functions.dispose() ;
        this.signal(e);
    }
}

export const ui_state = new UIState()
const reset_active = e=>{
   ui_state.reset_active(e)
}
window.reset_ui = e=>{
  ui_state.reset_ui(e)
};
window.__uistate = ui_state;

/**


^*/
export const card_state = mobx.makeAutoObservable({
    _minified : [],
    _redraw : [],
    toggle_minified_state (id_prefix, card){
        if (this.minified_cards.includes(card.id) ) {
            d3.select(`#${id_prefix}${card.id} .card-body`).style("height",null)
            this.minified_cards = {remove: card};
        } else {
            this.minified_cards = {add: card};
        }
    },
    get minified_cards (){
        return this._minified.map(d=>d.id);
    },
    set minified_cards (val){
        if (val.add) {
            if (Array.isArray(val.add)) {
               this._minified  = [...this._minified, ...val.add];
               this.redraw = _.map(val.add,x=>x.id);
            } else {
               this._minified.push(val.add);
               this.redraw = [val.add.id]
            }
        }
        if (val.remove) {
            this._minified = _.filter(this._minified, t=> t.id != val.remove.id);
            this.redraw = [val.remove.id]
        }
    },
    get redraw (){
       return this._redraw;
    },
    set redraw (val){
       return this._redraw = val;
    },
    register (cards){
        this.minified_cards = {add : cards};
    },
    reset (){
        this._minified = [];
    }
});

mobx.reaction(
    ()=> ui_state.attr,
    ()=>{
        if (ui_state.attr == null) {
            card_state.redraw = true;
        }
   }
);


// scan all htmx requests and if they ask for filters, then add them to the url
document.addEventListener('htmx:configRequest', event => {
  const elt = event.detail.elt;
  if ("data-check-for-filters" in elt.attributes){
      const filters = _.omitBy(ui_state.models[elt.attributes["data-model"].value].filters, _.isUndefined)
      event.detail.path += `?f=${btoa(JSON.stringify({filters}))}`
  }
});
// if the url is being replaced, them reset the UI and wipe out all mobX listeners
document.addEventListener("htmx:beforeRequest",event => {
   if ("hx-push-url" in event.target.attributes){
       ui_state.reset_ui();
   }
})
document.addEventListener("htmx:afterRequest",event => {
   if ("data-refresh-model" in event.target.attributes){
      const models = event.target.attributes["data-refresh-model"].value.split(",")
       _.each(models,m=>{
           const e = _.trim(m);
           if (e.startsWith("reload")){
              ui_state.signal(e);
           } else {
             ui_state.refresh_model_store(e);
           }
       })
   }
    d3.selectAll(".TMCommandBar").each(function(d){
        if (this.parentElement == document.body){
            this.remove()
        }
    })
})
           

const _dispose_functions = {
    funcs : [],
    dispose(){
        _.each(this.funcs, ob=>ob.func());
        this.funcs = []
    },
    get_node_ancestors(node){
        const path = []
        while(node) {
            path.push(node)
            element = node.parentElement
        }
        return path;
    },
    remove_node(node){
        const to_be_removed = [];
        _.each(this.funcs, ({node,func})=>{
            const ancestors = this.get_node_ancestors(node);
            if (ancestors.includes(e.detail.target)){
               func();
               to_be_removed.push(func)
            }
        });
        this.funcs = _.filter(this.funcs,d=> !to_be_removed.includes(d.func))
    }
};


export const autoRun = (node, _func)=>{
    const func =  mobx.autorun(_func);
    _dispose_functions.funcs.push(
        {node,func}
    );
    return func;
};

export const reaction = (node, test_func, _func)=>{
    const func =  mobx.reaction(test_func,_func);
    _dispose_functions.funcs.push(
        {node,func}
    );
    return func;
};


mobx.reaction(
    ()=>[ui_state.attr, ui_state.d],
    ()=>{
        d3.selectAll(".editor-insert").classed("d-none",true);
        d3.selectAll(".editor-normal").classed("d-none",false);
        if (ui_state.attr){
            const ids = ui_state.ids();
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
    if (_.isArray(val)){
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
            const val =  (force_list(model[x])|| []).map(x=>x.id);
            if (val.length) {
                obj[x] = val;
            }
        }  else if (["OneToOneRel", "ForeignKey"].includes(fields[x]) ){
            const val = (model[x] || {}).id || "";
            if (val){
                obj[x] = val;
            }
        } else if (x in model && !(x == "id" && _.isString(model.id) && model.id.startsWith("new"))){
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
        url = model.__url__;
    } else {
        f = fetch_recipies.POST;
        url = ui_state.models[model.__type__].main;
    }

    const resp = await f(url, 
        new URLSearchParams(obj).toString(), 
        true );
    if (resp.status == 200) {
        const data = await resp.json();
        if ("errors" in data) {
            //restore the backup from the failed POST/PUT
            // TODO add in error messages
        } else {
            //update the data
            ui_state.d = ui_state.update_store(data)
        }
    } else {
        const data = await fetch_recipies.GETjson(obj.__url__);
        Object.assign(model,data);
    }
};

const q = async (e)=>{
    if (ui_state.attr != "" && ui_state.is_fk()){
        let current_pks;
        const  attr  = ui_state.attr;
        const  d  = ui_state.d;
        const q = _.isUndefined(e) ? "" :  e.target.value;
        if (_.isArray(d[attr])) {
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

const toggle_fk_attr = async (result) => {
    let resp;
    if (result.selected){
        resp = await fetch_recipies.DELETE(result.__url__);
    } else {
        if (result.new){
            const obj = {...result};
            delete obj.id
            resp = await fetch_recipies.POST(
                result.__url__, 
                 new URLSearchParams(obj).toString(),
                true);
        } else {
            resp = await fetch_recipies.POST(result.__url__, "",true);
        }
    }
    if (ui_state.attr){
        const  attr  = ui_state.attr;
        const  d  = ui_state.d;
        const model_info =  ui_state.active_model_info;
        if (resp.status == 200) {
            const obj_refresh_resp = await fetch_recipies.GET(ui_state.d.__url__);
            if (obj_refresh_resp.status == 200){
                const data = await  obj_refresh_resp.json()
                d[attr] = data[attr];
            }
            return true;
        } else {
            return false;
        }
    }
};

d3.selection.prototype.styles = function(attrs){
    const ns = this.nodes()
    for (var i in this.nodes()){
        for ( var key in attrs ){
          this.node().style[key]  = attrs[key];
        }
    }
    return this;
}
d3.selection.prototype.attrs = function(attrs){
    const ns = this.nodes()
    for (var i in this.nodes()){
        for ( var key in attrs ){
          ns[i].setAttribute(key, attrs[key]);
        }
    }
    return this;
}
d3.selection.prototype.setup_htmx = function(){
    const ns = this.nodes()
    for (var i in this.nodes()){
        htmx.process(ns[i]);
    }
    return this;
}
d3.selection.prototype.select_parent = function(){
   return d3.select(this.node().parentElement);
}

d3.selection.prototype.last = function() {
  const last = this.size() - 1;
  return d3.select(this.nodes()[last]);
}


export const make_delete_button = function(selection, d, key, models_to_refresh,options={}){
    const {html="X",_class="btn btn-outline-danger"} = options;
    if (!selection.selectAll("button").empty()) {
        // already been created, so bail
        return;
    }
    if (d.__perms__.DELETE) {
        selection.selectAll("button")
           .data([d],key)
           .join("button")
              .attr("type","button")
              .attr("class",`${_class} p-1 me-1 ms-1 ` )
              .html(html)
            .attrs({
                "data-bs-toggle":"modal",
                "data-bs-target":`#delete_modal`
            })
              .on("click", e=>{
                d3.select("#modal_delete_button")
                  .attrs({
                    "hx-delete" : d.__url__,
                    "data-refresh-model" : models_to_refresh,
                    "hx-swap" : "none",
                  })
                  .setup_htmx();
              });
    }
}

export const make_cancel_button = function(selection){
    selection
            .append("button")
            .classed("btn-close ms-2",true)
            .attr("aria-label","Close")
            .on("click", reset_active)
    };

export const make_right_dropdown = function(selection, call, options={}){
    const {_class="btn btn-light"} = options;
    selection
        .append("div")
            .classed("dropdown d-flex justify-content-end",true)
            .append("button")
                .classed(`${_class} m-0 p-1`,true)
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
    const observable_data = make_observable_data();
    prep_data(observable_data)
    const ids = ui_state.ids({attr,d: observable_data });
    const {on_change} = options;
    const {_class="btn btn-sm btn-light"} = options;
    if (!selection.selectAll("div").empty()) {
        // already been created, so bail
        return;
    }
    const sel = selection
        .append("div")
        .classed(`mb-1`, true);
    if (observable_data.__perms__.POST == false) {
        // no permision to POST so just put the title 
       sel.html(title)
        return;
    }

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
                send_model({...observable_data, [attr] : e.target.value});
                reset_active()
                this.value = "";
                if (on_change ){
                    _.delay(()=>{
                       ui_state.signal(on_change)
                    }, 100)
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
        .classed(`${_class} p-1 m-1`,true)
        .on("click", () => {
            d3.select(`#${ids.insert_input}`).node().value = "";
            ui_state.d = observable_data;
            ui_state.attr = attr;
        })
        .html(title)
};

export const fk_toggle = function(selection, result, attr="",options={}){
    const { on_change=null } = options;
    selection
       .append("div")
       .classed("form-check form-switch",true)
           .append("input")
           .attr("type","checkbox")
           .attr("role","switch")
           .attr("role",attr)
           .call(sel=>{
               sel.node().checked = result.selected 
           })
           .style("font-size","1.5em")
           .classed("form-check-input",true)
           .on("change",async e=>{
               await toggle_fk_attr(result) 
               result.selected = e.target.checked
               if (on_change){
                   if (_.isFunction(on_change)){
                       on_change(e)
                   } else {
                       _.delay(()=>{
                           document.dispatchEvent(new Event(on_change))
                       },100)
                   }
               }
           });
};

export const inplace_char_edit = function(selection,
                                    observable_data, 
                                    attr="",
                                    title="" , 
                                    options={} ){

    const {
        btn_class="btn-light", 
        on_change=null,
        input_class="",
        display_attr=attr,
        static_override=null,
        type="text"} = options;
    console.log(static_override)
    prep_data(observable_data)
    const ids = ui_state.ids({attr,d:observable_data})
    if (selection.select("#"+ids.normal).node()) {
        return;
    }

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
            type
        })
        .on("keyup",e => {
            keyup_esc(reset_active)(e)
            keyup_enter(e=>{
                send_model({...observable_data, [attr] : e.target.value});
                reset_active()
                if (on_change ){
                    _.delay(()=>{
                       ui_state.signal(on_change)
                    }, 100)
                }
            })(e)
        })
        .call(selection=>{
            autoRun(selection.node(),()=>selection.node().value = observable_data[attr])
        })
        .select_parent()
        .call(make_cancel_button)

    selection
        .append("div")
        .classed(`editor-normal ${attr}-row`,true)
        .attr("id",ids.normal)
        .append("button")
        .classed(`btn ${btn_class} p-1 m-1`,true)
        .on("click", () => {
            ui_state.d = observable_data;
            ui_state.attr = attr;
        })
        .call(selection=>{
            if (observable_data.__perms__.PUT == false) {
                // no permision so don't enter insert mode
               selection.attr("disabled","true")
            }
            autoRun(selection.node(),
                    ()=>{
                        selection.html(static_override || observable_data[display_attr] || "+")
                    }
            )
            selection.html(static_override || observable_data[display_attr] || "+")
        });

}

export const append_edit_attr = function(selection,observable_data, ...args ){
    const type = ui_state.models[observable_data.__type__].fields[args[0]]
    prep_data(observable_data)
    if (ui_state.is_fk(type)){
        append_edit_fk(selection,observable_data, ...args )
    }  else {
        append_edit_local_attr(selection,observable_data,  ...args )
    }
}

export const append_edit_local_attr = function(selection,observable_data, attr="",title="",options={}  ){
    const {on_change,display_attr=attr, add_bottom_margin=true} = options;
    const type = ui_state.models[observable_data.__type__].fields[attr]
    const ids = ui_state.ids({attr,d:observable_data})
    if (selection.select("#"+ids.insert).node() || !observable_data.__perms__["PUT"]) {
        return;
    }

    const set_active = e=>{
         ui_state.d = observable_data
         ui_state.attr = attr 
    }
    const sel = selection
        .append("div")
        .classed(`mb-1`, add_bottom_margin)

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
            "font-size" : "0.8em"
        })
        .call(function(selection){
            const normal_mode = selection
            if (type == "BooleanField"){
                normal_mode
                    .append("span")
                    .classed("me-2",true)
                    .style("padding", ".375rem .75rem")
                    .style( "font-size","1.0em")
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
                            send_model({...observable_data, [attr] :  e.target.checked});
                            if (on_change ){
                                _.delay(()=>{
                                   ui_state.signal(on_change)
                                }, 100)
                            }
                        })
                        .call(selecion=>{
                            autoRun(selection.node(),()=>selecion.node().checked=observable_data[attr] )
                        });

            } else if (type == "DateField"){
                normal_mode
                    .append("div")
                    .append("button")
                    .attr("type","button")
                    .style("font-size", "1em")
                    .classed("btn btn-link mb-1",true)
                    .on("click",set_active)
                    .html(title)
                .select_parent()
                .select_parent()
                    .append("div")
                    .classed("w-50 ",true)
                    .append("input")
                    .attr("type","date")
                    .style("font-size", "1em")
                    .classed("form-control ps-2 pe-0",true)
                    .call(selecion=>{
                        autoRun(selection.node(),()=>selecion.node().value = observable_data[attr] )
                    })
                    .on("change", e => {
                        send_model({...observable_data, [attr] : e.target.value});
                        if (on_change ){
                            _.delay(()=>{
                               ui_state.signal(on_change)
                            }, 100)
                        }
                    })


            } else if ([ "CharField" , "EmailField", "DecimalField", "URLField"].includes(type)){
                normal_mode
                    .style( "font-size","0.8em")
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1 w-25 text-start",true)
                    .style( "font-size","1em")
                    .on("click",set_active)
                    .html(title)
                .select_parent()
                    .append("div")
                    .classed("me-1 w-75 text-end",true)
                    .call(selecion=>{
                        autoRun(selection.node(),()=>{
                          selecion.html(observable_data[attr] )
                        })
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
                        "type" :   ({
                            "DecimalField" : "number",
                            "CharField" : "text",
                            "EmailField" : "email",
                            "URLField" : "url",
                        })[type]
                    })
                    .on("keyup",e => {
                        keyup_esc(reset_active)(e)
                        keyup_enter(e=>{
                            send_model({...observable_data, [attr] : e.target.value});
                            if (on_change ){
                                _.delay(()=>{
                                   ui_state.signal(on_change)
                                }, 100)
                            }
                            reset_active()
                        })(e)
                    })
                    .call(selection =>{
                        autoRun(selection.node(), ()=>selection.attr("value",observable_data[attr] ))
                    })
                .select_parent()
                .call(make_cancel_button)

            } else if (type == "TextField"){
                let update_func;
                normal_mode
                    .classed("justify-content-between",true)
                    .append("button")
                    .attr("type","button")
                    .classed("btn btn-link mb-1 text-start w-25",true)
                    .style( "font-size","1em")
                    .on("click", set_active)
                    .html(title)
                .select_parent()
                    .append("div")
                    .classed("me-1 text-start",true)
                    .call(sel=>{
                        update_func =  ()=>sel.html(observable_data[display_attr])
                        reaction(sel.node(), 
                                ()=>observable_data[display_attr],
                                update_func)
                    })
                _.delay(update_func)

                insert_mode
                    .classed("border p-1",true)
                    .append("div")
                    .styles({
                        "background-color" : "rgba(0,0,0,.03)",
                    })
                    .attr("class","d-flex justify-content-between align-items-center border p-1 w-100")
                    .append("div")
                        .classed(" fw-bold pe-3 ps-3",true)
                        .attr("id", ids.insert_label)
                        .html(title)
                    .select_parent()
                        .append("div")
                        .classed("",true)
                        .styles({
                            "overflow-x" : "hidden",
                        })
                        .attr("id", ids.insert_label+"command-bar")
                .select_parent()
                .select_parent()
                    .append("textarea")
                    .classed("form-control mt-1",true)
                    .attr("id",ids.insert_input)
                    .attr("rows", 5)
                    .attr("name", attr)
                    .call(selection =>{
                        const content =  observable_data[attr] || "*  \n*  \n*  ";
                        const element =  selection.node();
                        autoRun(selection.node(),()=>{
                          selection.node().value = observable_data[attr];
                        })
                        const editor =  new TinyMDE.Editor({content, element});
                        new TinyMDE.CommandBar({
                            element: ids.insert_label+"command-bar",
                            editor
                        })
                    })
                .select_parent()
                    .append("div")
                    .classed("btn-group pt-2",true)
                        .append("button")
                        .classed("btn btn-sm btn-success" ,true)
                        .html("Save")
                        .on("click",()=>{
                            const input = d3.select(`#${ids.insert_input}`).node();
                            send_model({...observable_data, [attr] : input.value});
                            if (on_change ){
                                _.delay(()=>{
                                   ui_state.signal(on_change)
                                }, 100)
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
    if (selection.select("#"+ids.insert).node()) {
        return;
    }
    const sel = selection
        .append("div")
        .classed(`mb-1 `, true)
    const set_active = e=>{
         ui_state.d = observable_data
         ui_state.attr = attr 
    }

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
            .classed("form-control ms-2 ps-2 pe-0",true)
            .attrs({
                "type":"text",
                "id" :  ids.insert_input,
                "aria-describedby" : ids.insert_label,
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
                reaction(selection.node(),  
                    ()=> ui_state.search_results.slice(),
                    ()=>{
                    if (ui_state.d && 
                        ui_state.d.id == observable_data.id && 
                        ui_state.attr == attr){
                        selection
                            .selectAll("li")
                            .data(ui_state.search_results, d=> [d.id,d.selected] )
                            .join("li")
                            .classed("list-group-item d-flex p-1 me-1 border-0  align-items-stretch",true)
                            .selectAll("span.result-container")
                            .data(d=>[d], d=> [d.id,d.selected] )
                            .join("span")
                            .classed("result-container rounded p-1", true)
                            .style("border", d =>  `2px solid ${d.selected ? ui_state.models[d.__type__].hex : "#fff"}`)
                            .style("background-color", d=> ui_state.models[d.__type__].rgba)
                            .selectAll("button")
                            .data(d=>[d], d=> [d.id,d.selected] )
                            .join("button")
                            .on("click", async (e,d)=>{
                                if (await toggle_fk_attr(d)){
                                    ui_state.reset_active();
                                    if (on_change ){
                                        _.delay(()=>{
                                           ui_state.signal(on_change)
                                        }, 100)
                                    }
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

    let update_normal_mode;

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
                    "font-size" : "1em",
                    "line-height" : "1.5",
                    "padding": ".375rem .75rem",
                })
                .html(title)
            } else {
                selection
                .append("button")
                .attr("type","button")
                .classed("btn btn-link mb-1",true)
                .style( "font-size","1em")
                .on("click", set_active)
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
        .call(sel2=>{
            update_normal_mode = ()=>  {
                sel2
                   .selectAll("li")
                   .data(force_list(observable_data[attr]))
                   .join("li")
                   .classed("list-group-item d-flex p-1 me-1 bg-opacity-10 border-1 w-100 fw-bold text-nowrap ",true)
                   .style("background-color",dd=>  ui_state.models[dd.__type__].rgba)
                   .style("border-color",dd=>  ui_state.models[dd.__type__].hex)
                   .html(d=>d[name_attr])
            }
        });
        reaction(
            selection.node(),
            ()=>observable_data[attr],
            update_normal_mode
        );
        update_normal_mode();
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

