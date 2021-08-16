# To be inserted at 803753E4
#malloc = 0x81800000 - [[TOC Size]] - [[Reservation Size]]
  
bl _data 
b _code 
  _data: blrl 
  0: .asciz "codes.bin" 
  .align 2 
   
_code: 
mflr r3 
#lis r0, malloc@h 
lis r0, [[Reservation Location]]@h 
lmw r28, 0x8(sp) 			# r3 = path string 
#ori r4, r0, malloc@l 			# r4 = allocation address 
ori r4, r0, [[Reservation Location]]@l 	# r4 = allocation address 
addi r5, sp, 0x0C 			# r5 = returns size value 
bl 0x8001668c 				# $!_load_fromDVD 
  
_return: 
lwz r0, 0x001C (sp) 
.long 0