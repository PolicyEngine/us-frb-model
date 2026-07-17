' Program for simple simulation with MCE expectations
'
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
  wfcreate(wf=aaa,page={%mainpage}) q {%wfstart} {%wfend}

' FRB/US model names and locations
  %varmod = "stdver"
  %mcemod = "pfver"
  %model_path = "../mods/model.xml"

' Input database
%dbin  = "../data/longbase"

' MC expectations option ("-mcap","-mcap+wp","-all")
  %mcegroup = "-mcap+wp"

' Simulation start and length
  %simstart = "2020q1"
  !nsimqtrs = 60*4

  call dateshift(%simstart,%simend,!nsimqtrs-1)

' Number of quarters to show in graphs
  !graphqtrs = 40


' ****************************************************************
' Retrieve data, model equations and coefficients, set
' policy options, and compute tracking residuals 
' ****************************************************************

' Load equations and coefficients
  read_xml_model(path=%model_path,mce_vars=%mcegroup,mod_f=%mcemod)

' Load data
  dbopen %dbin as longdata
  fetch(d=longdata) *

' Data for extra variables associated with MC expectations
  smpl @all
  call mce_create_auxillary(m_zvars)

' Set monetary policy
  smpl @all
  call set_mp("dmpintay")

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
' Simulate a monetary policy shock 
' *************************************************************

  %sufsim = "_1"
  {%varmod}.scenario(n,a={%sufsim}) "sim"
  {%mcemod}.scenario(n,a={%sufsim}) "sim"

  smpl %simstart %simstart
  rffintay_a = rffintay_a + 1

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
  %title = " Macroeconomic Effects of Funds Rate Shock\r"
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


