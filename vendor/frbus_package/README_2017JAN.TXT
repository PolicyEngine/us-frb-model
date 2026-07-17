
The February 2017 release of the FRB/US Model Package contains some
significant changes.  The most important of these are described in
section 3.

(1)  All equations have been reestimated over sample periods that now
     end in 2015q4.  In general, revisions to coefficients are small
     and simulation properties are little changed.  The functional
     forms of equations have not been modified.

(2)  An error has been fixed in the subroutines used to run simulations
     when expectations are model-consistent involving the option to
     reset terminal conditions.

(3)  Major changes have been made to the way FRB/US equations and
     coefficients are stored in the package and loaded into EViews.
     Associated with these changes are revisions to all of the
     provided simulation programs.  Users who have written their own
     programs based on earlier releases of the package and wish to use
     them with the new release will need to revise their programs.
     Examples of the needed revisions are presented below.  Additional
     information on the new procedures is presented in the Simulation
     Basics document.

     (A) Revisions to the way the FRB/US equations and coefficients are
     stored

     In earlier releases of the package, the structure of FRB/US
     equations and the values of coefficients were stored in four text
     files in the mods subdirectory.  A separate "varinfo" file
     contained additional information such as the set of equations
     that receive shocks in stochastic simulations.  In the current
     release, equations, coefficients, and related information all
     everything is contained in a single XML file named model.xml.

     (B) Revisions to the way FRB/US equations and coefficients are
     loaded

     In earlier releases of the package, equations, coefficients, and
     related information were loaded into EViews using the six add-in
     commands that were provided as part of the package.  In the
     current release, all loading functions taken care of by a single
     add-in named read_xml_model.  The new add-in must be installed by
     starting EViews and then executing the program named regadd.prg
     that is located in the addins subdirectory.

     (C) An example of how to revise a program in which expectations
     are VAR-based

     - old code

       %varmod = "stdver"
       %varpath = "../mods/"
       ld_frbus_eqs(modelname=%varmod,modelpath=%varpath)  
       ld_frbus_cfs(modelname=%varmod,modelpath=%varpath)

     - new code

       %varmod = "stdver"
       %model_path = "../mods/model.xml"
       read_xml_model(path=%model_path)

     (D) An example of additional changes needed in a program that
     runs stochastic simulations

     - old code

       for !i = 1 to vinfo_size 
         %vname = @word(vinfo_vname,!i)
         %stoch = @word(vinfo_stoch,!i)
         if %stoch <> "NO" then
           %tmp = %tmp + " " + %vname
           endif
         next

     - new code

       for !i = 1 to @wcount(m_variable_names)
         %vname = @word(m_variable_names, !i)
         %stoch = @word(m_stoch, !i)
         if %stoch <> "NO" then
           %tmp = %tmp + " " + %vname
           endif
         next

     (E) An example of how to revise a program in which expectations
     in asset pricing and wage and price setting are model consistent

     - old code

       %varmod = "stdver"
       %varpath = "../mods/"
       %mcemod = "pfver"
       %mcepath = "../mods/"
       %mcvars_wp = "yes"
       %mcvars_all = "no"
       %zvars = "zdivgr zgap05 zgap10 zgap30 zrff5 zrff10 zrff30 "
       %zvars = %zvars + " zpi10 zpi10f zpic30 zpib5 zpic58 "
       if %mcvars_wp = "yes" and %mcvars_all = "no" then
         %zvars = %zvars + "zpicxfe zpieci "
         endif
       if %mcvars_all = "yes" then
         %zvars = %zvars + "zpicxfe zpieci "
         %zvars = %zvars + "zecd zeco zeh zgapc2 zlhp zpi5 zvpd zvpi zvps "
         %zvars = %zvars + " zxbd zxbi zxbs zyh zyhp zyht zynid "
         endif
       call mce_load_frbus("mce_vars=%zvars,mod_b=%varmod,
            path_b=%varpath,mod_f=%mcemod,path_f=%mcepath")
       smpl @all
       call make_frbus_mcevars(%zvars)

       %modstr = "mod_b=%varmod,mod_f=%mcemod,mce_vars=%zvars"

     - new code

       %varmod = "stdver"
       %mcemod = "pfver"
       %model_path = "../mods/model.xml"
       %mcegroup = "-mcap+wp"
       read_xml_model(path=%model_path,mce_vars=%mcegroup,mod_f=%mcemod)
       smpl @all
       call mce_create_auxillary(m_zvars)

       %modstr = "mod_b=%varmod,mod_f=%mcemod,mce_vars=m_zvars"

