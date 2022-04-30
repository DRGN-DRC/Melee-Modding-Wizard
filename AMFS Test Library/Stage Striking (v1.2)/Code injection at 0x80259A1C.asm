# To be inserted at 0x80259A1C

# Prevents striked stages from 
# being randomly selected (part 2/2)

# - actually more like part 1 though...
# - ensures the "already chosen" flag at SSS_stage struct +0x4 gets reset back to 0 if necessary
# - fixes bug in 4.06 with striking down to a single stage, then randomly selecting it twice 
#   in a row and the second time going to Peach's Castle 

lwz r3,0(r28)	# load JObj pointer
cmpwi r3,0	# this will be 0 if "RANDOM" stage select is ON
beq- END
lis r5,0x8040
ori r5,r5,0x6708	# make sure the struct is initialized
lwz r4,0(r3)
cmpw r4,r5
bne- END
lhz	r4,0x14(r3)
cmpwi r4,0
bne-	END
lis r3,0x8025
ori r3,r3,0x9a38
mtlr r3
blr
END:
lwz r0,4(r28)	# default code line