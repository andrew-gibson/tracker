
import  { append_edit_attr,ui_state, make_right_dropdown,autoRun, is_null,create_button, inplace_edit} from "d3-ui";

export const task_state = mobx.makeAutoObservable({
    tasks : [],
    _minified : [],
    _redraw : Math.random(),
    show_done : true,
    toggle_minified_state (task){
        if (this.minified_tasks.includes(task.id) ) {
            d3.select(`#task${task.id} .card-body`).style("height",null)
            this.minified_tasks = {remove: task};
        } else {
            this.minified_tasks = {add: task};
        }
    },
    get minified_tasks (){
        return this._minified.map(d=>d.id);
    },
    set minified_tasks (val){
        if (val.add) {
            if (Array.isArray(val.add)) {
               this._minified  = [...this._minified, ...val.add];
            } else {
               this._minified.push(val.add);
            }
            this.redraw = true;
        }
        if (val.remove) {
            this._minified = _.filter(this._minified, t=> t.id != val.remove.id);
        }
    },
    get redraw (){
       return this._redraw;
    },
    set redraw (x){
       this._redraw = Math.random();
    },
    unset_height(task){
        if (task.__type__ == "project.Task") {
           d3.select(`#task${task.id} .card-body`).style("height",null)
        }
    },
    register (tasks){
        this.tasks = [...this.tasks, ...tasks];
        this.minified_tasks = {add : [...tasks]};
        ui_state.active_elements = [...ui_state.active_elements, ...tasks]
    },
});

autoRun(()=>{
    if (ui_state.active == null) {
        task_state.redraw = true;
    }
})

export const project_summary =  project => {
    const observable_data = mobx.makeAutoObservable( project);
    const root = d3.select(`#project${project.id}`)
        .call(function(selection){
            selection.select(".card-header").remove();
            const body_sel = selection.select(".card-body");
            append_edit_attr(body_sel, observable_data, "name", "Name");
            append_edit_attr(body_sel, observable_data, "text","Description");
            append_edit_attr(body_sel, observable_data,"point_of_contact", "Contact");
            append_edit_attr(body_sel, observable_data,"tags", "Tags");
            append_edit_attr(body_sel, observable_data,"teams", "Teams");
            create_button( selection.select(".card-footer"), 
                          ()=>mobx.makeAutoObservable({name:"",__type__:"project.Stream",project:observable_data}),
                          "name",
                          "+ Workstream",
                        {on_change : "reloadTasks"})
        })
    ui_state.active_elements.push(root)
};

export const task_summaries = tasks=>{
  _.each(tasks, task=> {
    const observable_data = mobx.makeAutoObservable({...task});

    if (d3.select(`#task${observable_data.id}`).node() == null){
        return;
    }

    d3.select(`#task${observable_data.id}`)
        .data([task])
        .call(function(selection){
            const header_sel =  selection.select(".card-header");
            const header_left = header_sel.append("div").classed("flex-fill",true);
            const body_sel = selection.select(".card-body");
            const footer_sel = selection.select(".card-footer");

           inplace_edit(header_left.append("div").style("width","15%").style("display","inline-block"), observable_data, "order", "Order",{btn_class : "btn-outline-primary", on_change : "reloadTasks", input_class : "w-25"} );
           inplace_edit(header_left.append("div").style("width","85%").style("display","inline-block"), observable_data, "name", "Name");
           const hx_args =  {
                "hx-delete" : ui_state.models["project.Task"].rest_pk.replace("__pk__", task.id),
                "hx-on::after-request"  :  "window.reset_ui('reloadTasks')",
                "hx-swap" : "none",
           }
           make_right_dropdown(header_sel,dropdown=>{
                dropdown
                    .append("li")
                        .append("a")    
                            .classed("dropdown-item text-end",true)
                            .html("Deete")
                            .attrs(window.delete_modal.attrs)
                            .on("click", e=>{
                                window.delete_modal(hx_args);
                            })
           });

            autoRun(()=>{
                task_state.redraw
                body_sel.html("")
                _.each([ ["text","Notes",""],
                        ["start_date", "Start Date",""],
                        ["target_date","Target Date",""],
                        ["lead", "Contact",""],
                        ["teams", "Teams",""],
                        ["competency", "Competency",""],
                        ["stream", "Stream",{on_change : "reloadTasks"}]], 
                    args=>{
                        if(task_state.minified_tasks.includes(observable_data.id) && !is_null(observable_data[args[0]])){
                            append_edit_attr(body_sel, observable_data, ...args);
                        } else if ( !task_state.minified_tasks.includes(observable_data.id)){
                            append_edit_attr(body_sel, observable_data, ...args);
                        }
                });

                footer_sel   
                    .selectAll("div.left")                                                 
                    .data([1])
                    .join("div")
                    .classed("left fs-6 d-flex justify-content-center align-items-center expand-task text-body-tertiary text-body", true)
                    .html("")
                    .append("button")
                    .classed("btn btn-small btn-light p-1 mb-1", true)
                    .html(d=> task_state.minified_tasks.includes(observable_data.id) ? "+" : "-")
                    .on("click", e => {
                        task_state.toggle_minified_state(task)
                    });
            });

            footer_sel   
                 .classed("d-flex justify-content-between align-items-center", true)
                 .append("div")
                 .call(function(foodter_sel){
                    append_edit_attr(foodter_sel, observable_data, "done", "Done",{on_change : "reloadTasks"});
                 })
        })
  });
  task_state.register(tasks);
};
