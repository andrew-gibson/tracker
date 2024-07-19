import  {ui_state, inplace_char_edit,make_delete_button} from "d3-ui";
export const stream_mini = (stream)=>{
    const observable_data = mobx.makeAutoObservable(stream);

    if (d3.select(`#stream${stream.id}`).node() == null){
        return;
    }
    d3.select(`#stream${stream.id}`)
        .data([observable_data])
        .attr("class","border-bottom fs-3 mb-2 p-1 d-flex align-items-center justify-content-between pe-0" )
        .call(function(selection){
            const d = selection.datum();
            inplace_char_edit(selection.append("span"), observable_data, "name", "Name",{display_attr : "name_count"});
            make_delete_button(selection.append("div"), d,d=>d.id, "reloadTasks")
        })
    d3.selectAll(`#stream${stream.id}`).node()
};
