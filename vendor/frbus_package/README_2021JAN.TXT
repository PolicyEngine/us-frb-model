The January 2021 release of the FRB/US Model Package contains
minor changes to some of the model's equations.

1.  The equations for GFDBTN and GFDBTNP have been modified to make GFDBTNP the variable dynamically linked to the government surplus (GFSRPN). In addition, the accounting convention regarding the contribution of (implied) government investment spending to government surplus (GFSRPN) has been simplified.

Previous equation: 	gfdbtn - gfdbtn_aerr = ugfdbt*(gfdbtn(-1)
                     - .25*(gfsrpn-0.36*egfen))

New equation:		gfdbtn - gfdbtn_aerr = ugfdbt*gfdbtnp


Previous equation: 	gfdbtnp - gfdbtnp_aerr = ugfdbtp*gfdbtn

New equation: 		gfdbtnp - gfdbtnp_aerr = ugfdbtp*(gfdbtnp(-1) - .25*gfsrpn)


Previous equation: 	gfsrpn - gfsrpn_aerr = tpn + tcin
                   	- egfln - 0.64*egfen - gtn - gfintn
                   	+ ugfsrp*xgdpn

New equation: 		gfsrpn - gfsrpn_aerr = tpn + tcin
                   	- egfln - egfen - gtn - gfintn
                   	+ ugfsrp*xgdpn


2. The equation of TRPT is updated to make GFDBTNP the revelant concept of debt when debt-to-GDP ratio targeting is selected as fiscal policy option.

Previous equation: 		trpt - trpt_aerr = dfpex * trptx
                  		+ dfpdbt * ( trpt(-1)
                  		+ y_trpt(1) * (gfdbtn(-1)/xgdpn(-1) - gfdrt(-1))
                  		+ y_trpt(2) * d( gfdbtn(-1)/xgdpn(-1) - gfdrt(-1), 0, 1 ) )
                  		+ dfpsrp * ( trpt(-1)
                  		+ y_trpt(3) * ((gfsrpn(-1)/xgdpn(-1))
                               - (gfsrt(-1)+0.005*xgap2(-1))))


New equation: 			trpt - trpt_aerr = dfpex * trptx
                  		+ dfpdbt * ( trpt(-1)
                  		+ y_trpt(1) * (gfdbtnp(-1)/xgdpn(-1) - gfdrt(-1))
                  		+ y_trpt(2) * d( gfdbtnp(-1)/xgdpn(-1) - gfdrt(-1), 0, 1 ) )
                  		+ dfpsrp * ( trpt(-1)
                  		+ y_trpt(3) * ((gfsrpn(-1)/xgdpn(-1))
                               - (gfsrt(-1)+0.005*xgap2(-1))))

3. The length of the window of the moving average computed in the equations of FXGAP, QECD and QEH is increased in order to improve their stability in light of the size of the economic fluctuations observed during the COVID-19 pandemic.

4. Two variables (KPS and LEFR) with no feedback in the model or use were eliminated.

5. Finally, the equation of RFFRULE is modified so that its relation to the policy rule is direct and linear. The ELB continues to be enforced in the RFF equation.

Previous equation:	rffrule - rffrule_aerr =  @recode((dmpex * rfffix
                       + dmprr  * (rrfix +  ( picxfe +  picxfe(-1) +  picxfe(-2) +  picxfe(-3))  / 4 )
                       + dmptay * rfftay
                       + dmptlr * rfftlr
                       + dmpintay * rffintay
                       + dmpalt * rffalt
                       + dmpgen * rffgen)>(rffmin),(dmpex * rfffix
                       + dmprr  * (rrfix +  ( picxfe +  picxfe(-1) +  picxfe(-2) +  picxfe(-3))  / 4 )
                       + dmptay * rfftay
                       + dmptlr * rfftlr
                       + dmpintay * rffintay
                       + dmpalt * rffalt
                       + dmpgen * rffgen),rffmin)

New equation: 		rffrule - rffrule_aerr =  dmpex * rfffix
                       + dmprr  * (rrfix +  ( picxfe +  picxfe(-1) +  picxfe(-2) +  picxfe(-3))  / 4 )
                       + dmptay * rfftay
                       + dmptlr * rfftlr
                       + dmpintay * rffintay
                       + dmpalt * rffalt
                       + dmpgen * rffgen
