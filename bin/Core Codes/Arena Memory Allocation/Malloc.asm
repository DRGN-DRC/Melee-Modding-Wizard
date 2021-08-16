# To be inserted at 80375324

lis r0, [[Reservation Size]]@h 
ori r4, r0, [[Reservation Size]]@l 
lwz r3, 0x0(r4) 
li r4, 4 
bl 0x80344514 
  
_return: 
stw r28, 0x0008 (sp) 
.long 0