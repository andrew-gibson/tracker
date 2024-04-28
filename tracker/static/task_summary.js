import  {append_edit_fk, append_edit_attr,ui_state, make_right_dropdown} from "d3-ui";
export const task_summary = (task=false)=>{
    const observable_data = mobx.makeAutoObservable(task);

    d3.select(`#task${task.id}`)
        .append("div")
        .data([observable_data])
        .join("div")
        .classed("col-4 border pe-0" ,true)
        .call(function(selection){
           make_right_dropdown(selection,dropdown=>{
                dropdown
                    .append("li")
                        .append("a")    
                            .classed("dropdown-item",true)
                            .attrs({
                                "hx-delete" : ui_state.models["project.Task"].rest_pk.replace("__pk__", observable_data.id),
                                "hx-on::after-request"  :  "window.reset_ui('reloadTasks')"
                            })
                            .html("Deete")
                            .setup_htmx();
            });
            append_edit_attr(selection, observable_data, "name", "Name");
            append_edit_attr(selection, observable_data, "text","Notes");
            append_edit_attr(selection, observable_data, "start_date", "Start Date");
            append_edit_attr(selection, observable_data, "target_date","Target Date");
            append_edit_fk(selection, observable_data,"lead", "Contact");
            append_edit_fk(selection, observable_data,"teams", "Teams");
            append_edit_fk(selection, observable_data,"competency", "Competency");
            append_edit_attr(selection, observable_data,"done", "Done");
        });
};
