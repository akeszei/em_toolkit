## Adapted to my preferences from: https://strucbio.biologie.uni-konstanz.de/ccp4wiki/index.php/Pauls-key-bindings-for-coot
## To load these hotkeys in Coot, go to drop-down menu ‘Calculate’ > ‘Run Script…’ > choose this file

#        Coot default hotkeys:
#        =================
#        D = decrease slab thickness
#        F = increase slab thickness
#        C = crosshair
#        N = decrease zoom
#        M = increase zoom
#        L = display label toggle
#        O = cycle/view NCS chains at this residue
#        P = go to nearest Ca
#        I = idle (spin molecule)
#
#        Custom mapping:
#        ======================
#        e = Regularize residues
#        E = Kill sidechain (stub)
#        r = Real space refine active residue
#        x = Real space refine active residue and auto-accept
#        R = Real space refine in a 3.5A sphere
#        t = Real space refine active residue and both flanking residues
#        T = Real space refine neighbouring residues
#        y = Auto-fit rotamer w/ rigid body fit
#        g = Go to blob under cursor
#        w = Add water at cursor
#        a = Undo
#        z = Redo


add_key_binding("Refine Active Residue", "r", lambda: manual_refine_residues(0))
add_key_binding("Refine Active Residue AA", "x", lambda: refine_active_residue())
add_key_binding("Triple Refine", "t", lambda: manual_refine_residues(1))
add_key_binding("Autofit Rotamer", "y", lambda: auto_fit_rotamer_active_residue())
add_key_binding("Pepflip", "q", lambda: pepflip_active_residue())
add_key_binding("Go To Blob", "g", lambda: blob_under_pointer_to_screen_centre())
add_key_binding("Add Water", "w", lambda: place_typed_atom_at_pointer("Water"))
add_key_binding("Eigen-flip Ligand", "B", lambda: flip_active_ligand())
add_key_binding("Undo", "a", lambda: apply_undo())
add_key_binding("Redo", "z", lambda: apply_redo())

def key_binding_func_1():
    active_atom = active_residue()
    if (not active_atom):
        print "No active atom"
    else:
        imol      = active_atom[0]
        chain_id  = active_atom[1]
        res_no    = active_atom[2]
        ins_code  = active_atom[3]
        atom_name = active_atom[4]
        alt_conf  = active_atom[5]
        add_terminal_residue(imol, chain_id, res_no, "auto", 1)
add_key_binding("Add terminal residue", "", lambda: key_binding_func_1())

def key_binding_func_2():
    active_atom = active_residue()
    if (not active_atom):
        print "No active atom"
    else:
        imol      = active_atom[0]
        chain_id  = active_atom[1]
        res_no    = active_atom[2]
        ins_code  = active_atom[3]
        atom_name = active_atom[4]
        alt_conf  = active_atom[5]
        fill_partial_residue(imol, chain_id, res_no, ins_code)
add_key_binding("Fill Partial", "k", lambda: key_binding_func_2())

add_key_binding("Kill Sidechain", "E", lambda:
                using_active_atom(delete_residue_sidechain,
                                  "aa_imol", "aa_chain_id", "aa_res_no", "aa_ins_code", 0))

refine_residue_sphere_radius = 3.5  # Angstroms
add_key_binding("Refine residue in a sphere", "R",
                lambda: sphere_refine(refine_residue_sphere_radius))

def key_binding_func_21():
    if not valid_map_molecule_qm(imol_refinement_map()):
        info_dialog("Must set the refinement map")
    else:
        # not using active atom
        active_atom = active_residue()
        if (not active_atom):
            add_status_bar_text("No active residue")
        else:
            imol      = active_atom[0]
            chain_id  = active_atom[1]
            res_no    = active_atom[2]
            ins_code  = active_atom[3]
            atom_name = active_atom[4]
            alt_conf  = active_atom[5]

            rc_spec = [chain_id, res_no, ins_code]
            ls = residues_near_residue(imol, rc_spec, 1.9)
            with_auto_accept([refine_residues, imol, [rc_spec] + ls])
add_key_binding("Neighbours Refine", "T", lambda: key_binding_func_21())

def key_binding_func_3():
    if (os.name == 'nt'):
        home = os.getenv('COOT_HOME')
    else:
        home = os.getenv('HOME')
    dir_1 = os.path.join(home, "data", "rnase")
    read_pdb(os.path.join(dir_1, "tutorial-modern.pdb"))
    make_and_draw_map(os.path.join(dir_1, "rnasa-1.8-all_refmac1.mtz"),
                      "/RNASE3GMP/COMPLEX/FWT",
                      "/RNASE3GMP/COMPLEX/PHWT",
                      "", 0, 0)
add_key_binding("Load RNAs files", "F9", lambda: key_binding_func_3())

def key_binding_func_4():
    keyboard_ghosts_mol = -1
    for mol in model_molecule_list():
        if (ncs_ghosts(mol)):
            keyboard_ghosts_mol = mol
            break
    if (draw_ncs_ghosts_state(keyboard_ghosts_mol) == 0):
        make_ncs_ghosts_maybe(keyboard_ghosts_mol)
        set_draw_ncs_ghosts(keyboard_ghosts_mol, 1)
    else:
        set_draw_ncs_ghosts(keyboard_ghosts_mol, 0)
add_key_binding("Toggle Ghosts", ":", lambda: key_binding_func_4())

add_key_binding("Hydrogens off", "[", lambda: set_draw_hydrogens(0, 0))
add_key_binding("Hydrogens on", "]", lambda: set_draw_hydrogens(0, 1))

def key_binding_func_5():
    active_atom = active_residue()
    if (not active_atom):
        add_status_bar_text("No active residue")
    else:
        imol      = active_atom[0]
        chain_id  = active_atom[1]
        res_no    = active_atom[2]
        ins_code  = active_atom[3]
        atom_name = active_atom[4]
        alt_conf  = active_atom[5]
        name = get_rotamer_name(imol, chain_id, res_no, ins_code)
        if (not name):
            add_status_bar_text("No Name found")
        else:
            if (name == ""):
                add_status_bar_text("No name for this")
            else:
                add_status_bar_text("Rotamer name: " + name)
add_key_binding("Rotamer name in Status Bar", "~", lambda: key_binding_func_5())

def key_binding_func_6():
    active_atom = active_residue()
    if (not active_atom):
        add_status_bar_text("No active residue")
    else:
        imol      = active_atom[0]
        chain_id  = active_atom[1]
        res_no    = active_atom[2]
        ins_code  = active_atom[3]
        atom_name = active_atom[4]
        alt_conf  = active_atom[5]
        regularize_zone(imol, chain_id,
                        res_no - 1, res_no + 1,
                        alt_conf)
add_key_binding("Regularize Residues", "e", lambda: key_binding_func_6())

def key_binding_func_7():
    using_active_atom([[fit_to_map_by_random_jiggle,
                        ["aa_imol", "aa_chain_id", "aa_res_no", "aa_ins_code"],
                        [100, 1.0]]])
add_key_binding("Jiggle Fit", "J", lambda: key_binding_func_7())

def key_binding_func_8():
    using_active_atom(add_terminal_residue,
                      "aa_imol", "aa_chain_id", "aa_res_no",
                      "auto", 1)
add_key_binding("Add Terminal Residue", "|", lambda: key_binding_func_8())

add_key_binding("Accept Baton Position", "`", lambda: accept_baton_position())
add_key_binding("Cootilus here", "N", lambda: find_nucleic_acids_local(6.0))
