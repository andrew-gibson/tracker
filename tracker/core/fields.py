from django.db.models import (
    BigAutoField as _BigAutoField,
    BooleanField as _BooleanField,
    CharField as _CharField,
    DateField as _DateField ,           
    DateTimeField as _DateTimeField ,       
    EmailField as _EmailField ,          
    JSONField as _JSONField ,           
    OneToOneField as _OneToOneField ,       
    ForeignKey as _ForeignKey ,          
    DecimalField as _DecimalField ,        
    PositiveIntegerField as _PositiveIntegerField ,
    ManyToManyField as _ManyToManyField ,     
)

def BigAutoField():
    pass
def BooleanField():
    pass
def CharField(*args,**kwargs):
    pass
def DateField():
    pass
def DateTimeField():
    pass
def EmailField():
    pass
def JSONField():
    pass
def OneToOneField(*args,text_trigger=False,search_field="name",**kwargs):
    f = _OneToOneField(*args,**kwargs)
    setattr(f,"__text_trigger__",text_trigger)
    setattr(f,"__search_field__",search_field)
    return f
def ForeignKey(*args,text_trigger=False,search_field="name",**kwargs):
    f = _ForeignKey(*args,**kwargs)
    setattr(f,"__text_trigger__",text_trigger)
    setattr(f,"__search_field__",search_field)
    return f
def DecimalField():
    pass
def PositiveIntegerField():
    pass
def ManyToManyField(*args,text_trigger=False,search_field="name",**kwargs):
    f = _ManyToManyField(*args,**kwargs)
    setattr(f,"__text_trigger__",text_trigger)
    setattr(f,"__search_field__",search_field)
    return f


