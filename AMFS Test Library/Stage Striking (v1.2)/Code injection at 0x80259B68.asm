# To be inserted at 0x80259B68

# Prevents striked stages from 
# being randomly selected (part 1/2)

lwzx	r30,r31,r4

cmpwi r30,0	# this will be 0 if "RANDOM" stage select is ON
beq- END
lis r5,0x8040
ori r5,r5,0x6708	# make sure the struct is initialized
lwz r6,0(r30)
cmpw r6,r5
bne- END
lhz	r30,0x14(r30)
cmpwi r30,0
bne-	END
lis r30,0x8025
ori r30,r30,0x9b8c
mtlr r30
blr
END:
lwzx	r0,r31,r0	# default code line