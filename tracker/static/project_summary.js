import  { append_edit_attr,ui_state, make_right_dropdown, create_button } from "d3-ui";

export const project_summary = project => {
    const observable_data = mobx.makeAutoObservable( project);
    const root = d3.select(`#project${project.id}`)
        .call(function(selection){
            const body_sel = selection.select(".card-body");
            const footer_sel = selection.select(".card-footer");
            const header_sel =  selection.select(".card-header");
            make_right_dropdown(header_sel,dropdown=>{
            dropdown
                .append("li")
                    .append("a")    
                        .classed("dropdown-item",true)
                        .attrs({
                            "hx-delete" : ui_state.models["project.Project"].main_pk.replace("__pk__", project.id),
                            "hx-on::after-request"  :  "window.reset_ui('reloadProjects')"
                        })
                        .html("Deete")
                        .setup_htmx()

            })
            header_sel
                .append("div")
                .classed(`mb-1 name-row editor-normal`, true)
                .append("button")
                .classed("btn btn-link pb-1 ps-0",true)
                .attrs({
                    "hx-replace-url":"true",
                    "hx-swap":"outerHTML",
                    "hx-target" : "#main-content",
                    "hx-get" : ui_state.models["project.Project"].main_pk.replace("__pk__", project.id),
                })
                .setup_htmx()
                .html(observable_data.name)
            append_edit_attr(body_sel, observable_data, "status","Status");
            append_edit_attr(body_sel, observable_data,"text", "Description");
            append_edit_attr(body_sel, observable_data,"streams", "Streams",{read_only:true, name_attr:"name_count"});
            append_edit_attr(body_sel, observable_data,"leads", "Leads");
            append_edit_attr(body_sel, observable_data,"tags", "Tags");
            append_edit_attr(body_sel, observable_data,"teams", "Teams");

            footer_sel   
                 .classed("d-flex justify-content-between align-items-center", true)
                 .append("div")
                 .call(function(foodter_sel){
                    append_edit_attr(foodter_sel, observable_data, "private", "Private");
                 })
        })
    ui_state.active_elements.push(root)
};
