' This MCE example program illustrates:
'
' 1. how to use a monetary policy rule that is not one of the policy
'   alternatives included in FRB/US;
' 2. how to add new MCE expectations variables;
' 3. how to drop one of the regular FRB/US equations as part of the process
'   of loading the model

' Most of the code needed illustrate these issues is located between
' the "start of new code" and "end of new code" comments below

' See the Simulation Basics document for information about
' this program


' *************************************************************
' Initial filename and parameter settings
' *************************************************************

' Subroutines
  include ../subs/master_library
  include ../subs/mce_solve_library

' Workfile    
  %wfstart = "1975q1"
  %wfend = "2125q4"
  %mainpage = "main"
wfclose(noerr)
  wfcreate(wf=aaa,page={%mainpage}) q {%wfstart} {%wfend}

' FRB/US model names and locations
  %varmod = "stdver"
  %mcemod = "pfver"
  %model_path = "../mods/model.xml"

' Input database
%dbin  = "../data/longbase"
' MC expectations option ("-mcap","-mcap+wp","-all")
  %mcegroup = "-mcap+wp"

' Simulation start and length (varies by expectations option)
  %simstart = "2020q1"
  !nsimqtrs = 60*4

  call dateshift(%simstart,%simend,!nsimqtrs-1)

' Number of quarters to show in graphs
  !graphqtrs = 40


' ****************************************************************
' Retrieve data, model equations and coefficients, set
' policy options, and compute tracking residuals 
' ****************************************************************

' Load equations and coefficients, dropping one of the FRB/US monetary
' policy rule equations (rffgen) so that it can be replace below with
' an alternative rule
  %vars = "allbut rffgen"
  read_xml_model(path=%model_path,mce_vars=%mcegroup,mod_f=%mcemod,vars=%vars)

' Load data
  dbopen %dbin as longdata
  fetch(d=longdata) *


' *****************************************************************************
' *****************************************************************************
' start of new code (aside from the changes to the read_model addin above
'             the call to set_mp below)

' Code a first-difference interest rate rule as rffgen.  The first-difference
' rule depends on the expected output gap three quarters ahead (zgap3) and
' on expected 4-qtr inflation three quarters ahead (zpic43).  The name of
'  each new expectation must start with a "z".
  {%varmod}.append rffgen-rffgen_aerr = rff(-1) + .5*(zpic43-pitarg) _
                   + .5*(zgap3-zgap3(-4))

' Add the MCE definitions of zgap3 and zpic43 to the forward-looking model,
' noting that the MCE names of these variables must start with a "w" rather
' than a "z".
  {%mcemod}.append wgap3-wgap3_aerr = xgap2(3)
  {%mcemod}.append wpic43-wpic43_aerr = picx4(3)
' Add expectations error equations to the MCE model
  {%mcemod}.append ezgap3 = zgap3-wgap3
  {%mcemod}.append ezpic43 = zpic43-wpic43

' Add to the backward-looking model simple equations for the new expectations
' variables.  Technically, these equations should be the appropriate VAR
' expectations formulas, but because in this program these expectations are
' always be MCE, the form of their backward-looking identities is not very
' important.
  {%varmod}.append zgap3-zgap3_aerr = .5*xgap2(-1)
  {%varmod}.append zpic43-zpic43_aerr = .5*picx4(-1)+.5*ptr(-1)

' Add the new MCE variables to the m_zvars string
  m_zvars = m_zvars + " zgap3 zpic43"

' Define baseline values of the new expectations variables
  smpl @all
  series zgap3 = xgap2(3)
  series zpic43 = picx4(3)

' Make sure that the baseline data for rffgen matches baseline rff
  rffgen = rff

' end of new code
' *****************************************************************************
' *****************************************************************************

' Data for extra variables associated with MC expectations
  smpl @all
  call mce_create_auxillary(m_zvars)

' Set monetary policy to use the first-difference policy rule (coded as rffgen)
  smpl @all
  call set_mp("dmpgen")

' Turn off zero bound and policy thresholds; hold policymaker's
' perceived equilibrium real interest rate constant for first 40 qts
  smpl @all
  dmptrsh = 0
  rffmin = -9999
  drstar = 1
  smpl %simstart %simstart + 39
  drstar = 0
  smpl @all

' Set fiscal policy
  smpl @all
  call set_fp("dfpsrp")

' Set _aerr variables to zero
  smpl @all
  {%varmod}.makegroup(a,n) endog @endog
  call groupnew("endog","_aerr")
  call group2zero("endog_aerr")

' Standard solution options
  {%varmod}.solveopt(o=b,g=12,z=1e-12)
  {%mcemod}.solveopt(o=b,g=12,z=1e-12)

' Assign baseline tracking add factors
  %suftrk = "_0"
  smpl %simstart %simend 
  {%varmod}.addassign @all
  {%varmod}.addinit(v=n) @all
  {%varmod}.scenario(n,a={%suftrk}) "track"
  {%varmod}.solve
  scalar mm = @max(@abs(xgap{%suftrk}-xgap))
  if mm > .0001 then
    statusline dynamic tracking simulation failed for {%varmod}
    stop
    endif
  {%mcemod}.addassign @all
  {%mcemod}.addinit(v=n) @all

' *************************************************************
' Simulate the effects of a one-percent consumption shock 
' *************************************************************

  %sufsim = "_1"
  {%varmod}.scenario(n,a={%sufsim}) "sim"
  {%mcemod}.scenario(n,a={%sufsim}) "sim"

  smpl %simstart %simstart
  eco_a = eco_a + .01

  %modstr = "mod_b=%varmod,mod_f=%mcemod,mce_vars=m_zvars"
  %algstr = "meth=qnewton"
  %simstr = "type=single"
  smpl %simstart %simend
  call mce_run(%modstr,%algstr,%simstr)


'***********************************************************
' Make a graph
'***********************************************************

  smpl %simstart %simstart + !graphqtrs - 1
  series zero = 0
  series d_rff = rff{%sufsim} - rff
  series d_rg10 = rg10{%sufsim} - rg10
  series d_lur = lur{%sufsim} - lur
  series d_pic4 = pic4{%sufsim} - pic4

  graph fig1a.line zero d_rff
  fig1a.addtext(t,just(c),font("arial",12)) Federal Funds Rate
  fig1a.legend -display

  graph fig1b.line zero d_rg10
  fig1b.addtext(t,just(c),font("arial",12)) 10-Year Treasury Yield
  fig1b.legend -display

  graph fig1c.line zero d_lur
  fig1c.addtext(t,just(c),font("arial",12)) Unemployment Rate
  fig1c.legend -display

  graph fig1d.line zero d_pic4
  fig1d.addtext(t,just(c),font("arial",12)) Inflation Rate (4-Quarter)
  fig1d.legend -display

  graph fig1.merge fig1a fig1b fig1c fig1d
  %title = " Macroeconomic Effects of a Shock to Consumption\r"
  if %mcvars_wp = "no" and %mcvars_all = "no" then
    %title = %title + "(MC Expectations in Asset Pricing)"
    endif
  if %mcvars_wp = "yes" and %mcvars_all = "no" then
    %title = %title + "(MC Expectations in Asset Pricing and Price-Wage Setting)"
    endif
  if %mcvars_all = "yes" then
    %title = %title + "(MC Expectations in All Sectors)"
    endif
  fig1.addtext(t,just(c),font("Arial",16)) {%title}
  fig1.align(2,1,1.25)
  show fig1


