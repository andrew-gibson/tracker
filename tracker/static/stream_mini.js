import  {ui_state, make_right_dropdown, inplace_char_edit,make_cancel_button, append_edit_attr,make_delete_button} from "d3-ui";
export const stream_mini = (stream)=>{
    const observable_data = mobx.makeAutoObservable(stream);

    if (d3.select(`#stream${stream.id}`).node() == null){
        return;
    }
    d3.select(`#stream${stream.id}`)
        .data([observable_data])
        .classed("border-bottom fs-3 mb-2 p-1 d-flex align-items-center justify-content-between pe-0" ,true)
        .append("span")
        .call(function(selection){
            inplace_char_edit(selection, observable_data, "name", "Name",{display_attr : "name_count"});
        })
        .select_parent()
        .call(function(selection){
            const d = selection.datum();
            make_right_dropdown(selection,dropdown=>{
                dropdown
                    .append("li")
                        .call(function(selection2){
                            make_delete_button(selection2, d,d=>d.id, "reloadTasks")
                        })
            })
        })
};
