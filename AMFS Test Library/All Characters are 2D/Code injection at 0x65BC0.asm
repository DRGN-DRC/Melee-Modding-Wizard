# To be inserted at 0x65BC0

# Check for the debug menu flag (non-zero indicates enabled)
lis r15, 0x8023
lwz r15, -0x770C(r15)
cmpwi r15, 0
beq+ OrigCodeLine 		# Not enabled; branch to orig code line

# Modified code line (set internal stage ID to 0x1B, for Flat Zone)
li r0, 0x1B
b End

OrigCodeLine:
lwz r0,136(r3)	  # Orig code line (load internal stage ID)

End:
b 0