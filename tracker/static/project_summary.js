import  { append_edit_attr,ui_state, make_right_dropdown, create_button } from "d3-ui";

export const project_summary = project => {
    const root = d3.select(`#project${project.id}`)
        .call(function(selection){
           const body_sel = selection.select(".card-body");
           const footer_sel = selection.select(".card-footer");
           const header_sel =  selection.select(".card-header");
           const delete_hx_args =  {
                "hx-delete" : project.__url__,
                "hx-on::after-request"  :  "window.reset_ui('reloadProjects')",
                "hx-swap" : "none",
           }
           make_right_dropdown(header_sel,dropdown=>{
                dropdown
                    .append("li")
                        .append("a")    
                            .classed("dropdown-item text-end",true)
                            .html("Delete")
                            .attrs(window.delete_modal.attrs)
                            .on("click", e=>{
                                window.delete_modal(delete_hx_args);
                            })
           });

           header_sel
                .append("div")
                .classed(`mb-1 name-row editor-normal`, true)
                .append("button")
                .classed("btn btn-link pb-1 ps-0 text-end",true)
                .attrs({
                    "hx-replace-url":"true",
                    "hx-target" : "#main-content",
                    "hx-get" : project.__url__,
                })
                .setup_htmx()
                .html(project.name)
            append_edit_attr(body_sel, project, "status","Status");
            append_edit_attr(body_sel, project,"text", "Summary");
            append_edit_attr(body_sel, project, "group","Team",{on_change : "reloadProjects"});
            append_edit_attr(body_sel, project,"streams", "Streams",{read_only:true, name_attr:"name_count"});
            append_edit_attr(body_sel, project,"lead", "Lead", {name_attr : "username"});
            append_edit_attr(body_sel, project,"project_manager", "Project Manager", {name_attr : "username"});
            append_edit_attr(body_sel, project,"project_team", "Project Team", {name_attr : "username"});
            append_edit_attr(body_sel, project,"tags", "Tags");
            append_edit_attr(body_sel, project,"partners", "Partners");

            footer_sel   
                 .classed("d-flex justify-content-between align-items-center", true)
                 .append("div")
                 .call(function(foodter_sel){
                    append_edit_attr(foodter_sel, project, "private", "Private");
                 })
        })
    ui_state.active_elements.push(root)
};
