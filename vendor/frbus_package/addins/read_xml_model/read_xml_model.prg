subroutine read_model_addin(string rm_path, string rm_mce_vars, string rm_mod_f, string rm_vars)


  scalar get_equations = 1
  scalar get_coeffs    = 1
  scalar get_forecast_info     = 0
  scalar get_varinfo   = 1

  scalar do_clean_up = 1



  string mod_b = "usename"

  string mod_f = @lower(rm_mod_f)
  if @isna(mod_f) then
    mod_f = "" 'make it empty instead of NA
  endif
  string coded = ""
  string skip = ""

  string vars = @lower(rm_vars)
  if vars = "" then
    vars = "-all"
  endif
  if @instr(vars,"allbut") then
    vars = @replace(vars,"allbut","-allbut")
  endif
  string mce_vars = @lower(rm_mce_vars)
  if mod_f <> ""  and (mce_vars = "" or @isna(mce_vars)) then
    @uiprompt("No mce_vars were specified in read_model!! mce_vars = " + mce_vars)
    stop
  endif


if (@mid(mce_vars,1,7) <> "-allbut") then

  if (@left(mce_vars,1) <> "z" and mce_vars <> "-all" and mce_vars <> "-mcap" and mce_vars <> "-wp" and mce_vars <> "-mcap+wp") then
    @uiprompt("The mce_vars group specification " + mce_vars + " is incorrect. Valid options are: -all, -mcap, -wp, -mcap+wp")
    stop

  endif

endif


    do_clean_up = 1
    string create_ez_eq = "yes"


  'Common objects
  scalar post_variable = 0
  scalar line_index = 0
  scalar m_varindex = 0
  string next_line = ""
  string m_varlist = " "
  scalar vinfo_found = 0
  scalar stoch_found = 0

  if get_varinfo = 1 then
    string m_variable_names
    string m_exog_string = " "
    string m_stoch = " "
    scalar stoch_index = 0
  endif


  ' Read the XML file and put it into an svector
  delete(noerr) xml_text
  text xml_text
  %aa = rm_path
  xml_text.append(file) %aa
  svector xml_text_v = xml_text.@svectornb 


  'Get the model name
  while 1<2
    call get_next_line
    if @instr(next_line, "<name>") then
      string m_model_name = @replace(next_line, "<name>", "")
      m_model_name = @replace(m_model_name, "</name>", "")
      exitloop
    endif
  wend


  ' Create model objects named appropriately if we need to
  if get_equations = 1 then  
    if mod_b <> "" then
      if mod_b = "usename" then
        mod_b = m_model_name
      endif
      model {mod_b}
    endif
    if mod_f <> "" then
      model {mod_f}
      string m_zvars = " "
    endif
  endif

  ' Start outermost loop that cycles through each variable and terminates with
  ' the </model> 
  while 1<2

    call get_next_line

    ' The exit condition
    if @instr(next_line,"</model>") then
      exitloop
    endif

    
    ' Start the loop that cycles inside each <variable>, </variable> tag
    if next_line = "<variable>" then
      call get_next_line
      vinfo_found = 0
      stoch_found = 0
      call process_variable_name 'returns the string varname with the variable's name
      
      ' The flag "post_variable" refers to whether we get that variables information 
      ' for the backwards looking model only. The metadata extracted in the xml is tied to the
      ' backwards looking variables.

      if get_varinfo = 1 then
        m_variable_names = m_variable_names + " " + varname
        call get_next_line
      endif

      while 1<2
        call get_next_line

        if get_equations = 1 or get_coeffs = 1 then

          if post_variable = 1 then
            if mod_b <> "" then
              if @instr(next_line, "<standard_equation>") then
                call process_standard_eq
              endif
            endif
          endif

          if mod_f <> "" then
            if @instr(next_line, "<mce_equation>") then
              statusline mce equation
              call process_mce_equation
            endif
          endif

        endif



        if post_variable = 1 then

          if get_varinfo = 1 then

            if @instr(next_line, "<stochastic_type>") then
              call process_stochastic_type
            endif

          endif

        endif

        if next_line = "</variable>" then
          exitloop
        endif

      wend ' End loop inside <variable> </variable>

      if get_varinfo = 1 then
        if stoch_found = 0 then
          m_stoch = m_stoch + " NO"
        endif
      endif
    endif



  wend

 ' check that model %mod_b contains an equation for each variable specified

  if @wcount(coded) <> 0 then 
     string wrongnames = @wnotin(@lower(coded),@lower(m_variable_names))
     if @wcount(wrongnames) <> 0 then
       %errstring = "Error in read_xml_model: The model"
       %errstring = %errstring + " does not contain expectation equation(s) intended to include for variable(s):  " + wrongnames
       %errstring = %errstring + ".  Execution stopped."
       @uiprompt(%errstring)
       stop
     endif
  endif
  if @wcount(skip) <> 0 then 
     string wrongnames = @wnotin(@lower(skip),@lower(m_variable_names))
     if @wcount(wrongnames) <> 0 then
       %errstring = "Error in read_xml_model: the model" 
       %errstring = %errstring + " does not contain expectation equation(s) intended to skip for variable(s):  " + wrongnames
       %errstring = %errstring + ".  Execution stopped."
       @uiprompt(%errstring)
       stop
     endif
  endif

  
  if do_clean_up = 1 then
    call clean_up
  endif

endsub



subroutine process_eviews_equation

  call get_next_line
  string eviews_eq = next_line

  while 1<2

    if @instr(eviews_eq, "</eviews_equation>") then  'pretest for oneliners
      exitloop
    endif

    call get_next_line
    if next_line= "</eviews_equation>" then
      exitloop
    endif
    eviews_eq = eviews_eq + next_line
  wend 
  eviews_eq = @replace(eviews_eq, "<eviews_equation>", "")
  eviews_eq = @replace(eviews_eq, "</eviews_equation>", "")
  eviews_eq = @replace(eviews_eq, "&gt;", ">")
  eviews_eq = @replace(eviews_eq, "&lt;", "<")
  {mod_b}.append {eviews_eq}

endsub


subroutine eviews_eq_mce

  call get_next_line 

  ' There is a mce description of arbitrary length that
  ' needs to be skipped over
  while 1<2
    if @instr(next_line, "<eviews_equation>") then
      exitloop
    else
      call get_next_line
    endif 
  wend


  ' Start processing on first line that contains <eviews_equation>
  string eviews_eq = next_line
  while 1<2

    if @instr(eviews_eq, "</eviews_equation>") then  'pretest for oneliners
      exitloop
    endif
    call get_next_line
    if next_line= "</eviews_equation>" then
      exitloop
    endif
    eviews_eq = eviews_eq + next_line
  wend 
  eviews_eq = @replace(eviews_eq, "<eviews_equation>", "")
  eviews_eq = @replace(eviews_eq, "</eviews_equation>", "")
  eviews_eq = @replace(eviews_eq, "&gt;", ">")
  eviews_eq = @replace(eviews_eq, "&lt;", "<")
  eviews_eq = @replace(eviews_eq, "y_z", "y_w")
  eviews_eq = @replace(eviews_eq, varname,  "w"+@mid(varname,2))

  {mod_f}.append {eviews_eq}
  m_zvars = m_zvars + " " + varname

  if create_ez_eq <> "no" then

    if varname <> "zyh" and varname <> "zyhp" and varname <> "zyht" then
      %tmp1 = "e"+varname + "=" + varname + "-" + "w"+@mid(varname,2)
    else
      %tmp1 = "e"+varname + "= log(" + varname + "/" + "w"+@mid(varname,2) + ")"
    endif
    {%mod_f}.append {%tmp1}

  endif




endsub


subroutine process_mce_equation

  call get_next_line


  string mce_group = next_line
  mce_group = @replace(mce_group, "<mce_group>", "")
  mce_group = @replace(mce_group, "</mce_group>", "")

  scalar process_mce = 0

  ' We've marked the mce variables into different groups so that a user
  ' may specify a group as oppposed to all the constituents of that group

  if mce_vars = "-all" then
    process_mce = 1
  endif
  if mce_vars = "-mcap" then
    if mce_group = "mcap" then
      process_mce = 1
    endif
  endif
  if mce_vars = "-wp" then
    if mce_group = "mcwp" then
      process_mce = 1
    endif
  endif
  if mce_vars = "-mcap+wp" then
    if mce_group = "mcwp" or mce_group = "mcap" then
      process_mce = 1
    endif
  endif
  if @instr(mce_vars, "-allbut") then
    %mce_names = @replace(mce_vars, "-allbut", "")
    string skip = %mce_names
    process_mce = 1
    for !j = 1 to @wcount(%mce_names)
      %z = @word(%mce_names,!j)
      if varname = %z then
	process_mce = 0
      endif
    next
  endif
  if @left(mce_vars,1) <> "-" then
    %mce_names = @replace(mce_vars, "-", "")
    string coded = %mce_names
    for !j = 1 to @wcount(%mce_names)
      %z = @word(%mce_names,!j)
      if varname = %z then
	process_mce = 1
      endif
    next
  endif



  if process_mce = 1 then

    if get_equations = 1 then
      call eviews_eq_mce
    endif

    if get_coeffs = 1 then

    ' Not all equations have coefficients, so we test for the existence
      ' of at least one before calling the subroutine
      while 1<2
        call get_next_line
        if @instr(next_line, "<coeff>") then
          call process_coeff_mce
        endif
        if @instr(next_line, "</mce_equation>") then
           exitloop
        endif
      wend

    endif
  endif

endsub


subroutine process_standard_eq

  if get_equations = 1 then
     call process_eviews_equation
  endif

  if get_coeffs = 1 then

    ' Not all equations have coefficients, so we test for the existence
    ' of at least one before calling the subroutine
    while 1<2
      call get_next_line
      if @instr(next_line, "<coeff>") then
        call process_coefficients
      endif
      if @instr(next_line,  "</standard_equation>") then
        exitloop
      endif
    wend

  endif

endsub


subroutine process_variable_name

  post_variable = 1
  string varname = @replace(next_line, "<name>", "")
  varname = @replace(varname, "</name>", "")

  'test whether it should be in the model.

  if @instr(vars, "-allbut") then
     %var_names = @replace(vars, "-allbut", "")
     for !j = 1 to @wcount(%var_names)
       %z = @word(%var_names,!j)
       if varname = %z then
	 post_variable = 0
       endif
     next
  endif
  if @left(vars,1) <> "-" then
     %var_names = @replace(vars, "-", "")
     post_variable = 0
     for !j = 1 to @wcount(%var_names)
       %z = @word(%var_names,!j)
       if varname = %z then
	 post_variable = 1
       endif
     next
  endif 

  ' Add the variable if the flag is non-zero
  if post_variable = 1 then
    m_varlist = m_varlist + " " + varname
    m_varindex = m_varindex + 1
  endif

endsub





subroutine process_stochastic_type

  stoch_index = stoch_index + 1
  stoch_found = 1

  %vstoch = @replace(next_line, "<stochastic_type>", "")
  %vstoch = @replace(%vstoch, "</stochastic_type>", "")

  m_stoch =  m_stoch + " " + %vstoch 

endsub 



subroutine process_coefficients

  ' the "next_line" will have <coeff> on entry

  string coeff_list = ""
  scalar num_coeff = 0
     
  while 1<2

    call get_next_line ' <cf_name>
    call get_next_line ' <cf_value>

    num_coeff = num_coeff + 1
    if num_coeff = 1 then
      %sep = ""
    else 
      %sep = ","
    endif
    string coeff = @replace(next_line, "<cf_value>", "")
    coeff = @replace(coeff, "</cf_value>", "")
    coeff_list = coeff_list +%sep + coeff 

    call get_next_line ' gets either </coeff> or </t_stat>
    ' There can optionally be a t_stat or distributed_lag_group, skip it if so.
    if @instr(next_line, "t_stat") then
      call get_next_line
    endif
    if @instr(next_line, "distributed_lag_group") then
      call get_next_line
    endif
    if @instr(next_line, "cf_formula") then
      call get_next_line
    endif

    call get_next_line ' Will either be <coeff> or another tag signalling
                       ' the end of the coefficients.

    if @instr(next_line, "<coeff>") = 0 then
      exitloop
    endif

  wend

  %num_coeff = @str(num_coeff)
  %beta_name = "y_" + varname
     
  coef({%num_coeff}) {%beta_name}
  {%beta_name}.fill  {coeff_list}

endsub

subroutine process_coeff_mce

  string coeff_list = ""
  scalar num_coeff = 0
     
  while 1<2

    call get_next_line ' <cf_name>
    call get_next_line ' <cf_value>

    num_coeff = num_coeff + 1
    if num_coeff = 1 then
      %sep = ""
    else 
      %sep = ","
    endif
    string coeff = @replace(next_line, "<cf_value>", "")
    coeff = @replace(coeff, "</cf_value>", "")
    coeff_list = coeff_list +%sep + coeff 

    call get_next_line
    ' There can optionally be a t_stat, skip it if so.
    if @instr(next_line, "t_stat") then
      call get_next_line
    endif

    call get_next_line ' Will either be <coeff> or another tag signalling
                       ' the end of the coefficients.

    if @instr(next_line, "<coeff>") = 0 then
      exitloop
    endif

  wend

  %num_coeff = @str(num_coeff)
  %beta_name = "y_" + varname
  %beta_name = @replace(%beta_name, "y_z", "y_w")
  coef({%num_coeff}) {%beta_name}
  {%beta_name}.fill  {coeff_list}

endsub




subroutine get_next_line
  
  line_index = line_index + 1
  next_line= xml_text_v(line_index)

endsub





subroutine clean_up


  'Make this separate from clean-up
  '''''''''''''''''''''''''''''''''''''
  if get_forecast_info = 1 then
    if @isobject("m_exog_string") then
      svector m_endogenous
      string m_endog_string
      m_endog_string = @wdrop(m_varlist, m_exog_string)
      m_endogenous = @wsplit(m_endog_string)
    endif
  endif
 ''''''''''''''''''''''

  if @isobject("coeff") then
  delete coeff
  endif
  if @isobject("coeff_list") then
  delete coeff_list
  endif
  if @isobject("eviews_eq") then
  delete eviews_eq
  endif
  if @isobject("num_coeff") then
  delete num_coeff
  endif
  if @isobject("stoch_index") then
  delete stoch_index
  endif
  if @isobject("varname") then
  delete varname
  endif
  if @isobject("xml_text") then
  delete xml_text
  endif
  if @isobject("xml_text_v") then
    delete xml_text_v
  endif
  if @isobject("horizon_text") then
    delete horizon_text
  endif
  if @isobject("code_text") then
    delete code_text
  endif
  if @isobject("vtype") then
    delete vtype
  endif
  if @isobject("process_mce") then
    delete process_mce
  endif
  if @isobject("mce_group") then
    delete mce_group
  endif



  delete mod_b
  delete mod_f
  delete mce_vars
  delete vars
  delete post_variable
  delete line_index
  delete m_varindex
  delete next_line
  delete m_varlist
  delete stoch_found
  delete vinfo_found

  delete create_ez_eq
  delete do_clean_up
  delete get_coeffs
  delete get_equations
  delete get_forecast_info
  delete get_varinfo

endsub


subroutine check_addin_options(string %addin_name, string %valid_options)

' Checks the options passd to addin %addin_name against valid option path
' %valid_options. Stops execution if invalid option was specified.

  !ii = 0
  !endit = 0
  while !endit = 0
    !ii = !ii + 1 
    if @len(@option(!ii)) > 0 then
      %passed_in_option =  @mid(@option(!ii),1, @instr(@option(!ii),"=")-1)
      while @instr(%passed_in_option, " ")
        %passed_in_option = @replace(%passed_in_option, " ", "")
      wend
      if @instr(%valid_options,@lower(%passed_in_option)) = 0  then
        @uiprompt("Option *" + %passed_in_option + "* was not recognized in " + %addin_name  + " command! Program stopped! Valid options are: " + %valid_options)
        stop
      endif
    else
      !endit = 1 
    endif
  wend

endsub



'************************************
' Start of addin execution
'************************************


'process arguments
 if @len(%args) > 0 then
 	@uiprompt("No arguments in read_model command!")
         stop
 endif

call check_addin_options("read_model","path  mce_vars mod_f vars")

if @len(@option(1)) > 0 then

	%temp = @equaloption("path")
	if @len(%temp)>0 then
		%path = @lower(%temp)
        endif

	%temp = @equaloption("mod_f")
	if @len(%temp)>0 then
		%mod_f = @lower(%temp)
        endif

	%temp = @equaloption("mce_vars")
	if @len(%temp)>0 then
		%mce_vars = @lower(%temp)
        endif

	%temp = @equaloption("vars")
	if @len(%temp)>0 then
		%vars = @lower(%temp)
        endif
endif


call read_model_addin(%path, %mce_vars, %mod_f, %vars)













