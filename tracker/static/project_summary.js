import  {append_edit_fk, append_edit_attr,ui_state } from "d3-ui";
export const project_summary = (project,add_title_links=false)=>{
    const observable_data = mobx.makeAutoObservable( project);
    const root = d3.select(`#project${project.id}`)
        .selectAll("div")
        .data([observable_data])
        .join("div")
        .classed("border pe-0" ,true)
        .call(function(selection){
            if (add_title_links){
                selection
                    .append("div")
                    .classed(`mb-1 name-row`, true)
                    .append("button")
                    .classed("btn btn-link pb-1 ps-0",true)
                    .attrs({
                        "hx-replace-url":"true",
                        "hx-swap":"outerHTML",
                        "hx-target" : "#main-content",
                        "hx-get" : ui_state.models["project.Project"].rest_pk.replace("__pk__", project.id),
                    })
                    .setup_htmx()
                    .html(d=>d.name)
                    .select_parent()
                    .select_parent()
                    .append("div")
                    .classed("text-dark text-opacity-75 lh-1 mb-2 text-row",true)
                    .styles({
                        "font-size" : "0.8em",
                    })
                    .html(d=>d.text)
            } else {
                append_edit_attr(selection, observable_data, "name", "Name");
                append_edit_attr(selection, observable_data, "text","Description");
            }
        })
        .call(function(selection){
            append_edit_fk(selection, observable_data,"streams", "Streams");
            append_edit_fk(selection, observable_data,"point_of_contact", "Contact");
            append_edit_fk(selection, observable_data,"tags", "Tags");
            append_edit_fk(selection, observable_data,"teams", "Teams");
        })
    ui_state.active_elements.push(root)
};
