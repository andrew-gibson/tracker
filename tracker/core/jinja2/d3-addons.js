 d3.selection.prototype.styles = function(attrs){
    for ( key in attrs ){
      this.node().style[key]  = attrs[key];
    }
    return this;
}
d3.selection.prototype.attrs = function(attrs){
    for ( key in attrs ){
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
