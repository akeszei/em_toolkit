"""
## Adapted to my preferences from: https://strucbio.biologie.uni-konstanz.de/ccp4wiki/index.php/Pauls-key-bindings-for-coot
## For interface functions see: https://www2.mrc-lmb.cam.ac.uk/personal/pemsley/coot/docs/html/c-interface_8h.html#a370e0bdd24c903cd2cbd0fe9eeef5fd1
## To load these hotkeys in Coot, go to drop-down menu: Calculate > Run Script > choose this file

    Coot default hotkeys:
    =================
    D = decrease slab thickness
    F = increase slab thickness
    C = crosshair
    N = decrease zoom
    M = increase zoom
    L = display label toggle
    O = cycle/view NCS chains at this residue
    P = go to nearest Ca
    I = idle (spin molecule)

    Custom mapping:
    ======================
NOTE: The goal of this mapping is to minimize the need to move the mouse away from the structure we are working on by allowing the user to activate the main two buttons for refinement/regularization by 'r' and 't' buttons, while quickly toggling between secondary structure restraints 'Tab = None', 'q = alpha helix', 'w = beta sheet' [see the active state at the top menu beside the place ligand button]. Other useful functions for rapid refinement include quickly swapping side chains for stubs 'E', area refinement 'R', and fix atom 'F' [note: fix atom gui needs to be open for correct behavior], and flip peptide 'W'

    r = Activate real space refinement (click 2 atoms); equivalent to clicking button on gui
    t = Activate regularize zome refinement (click 2 atoms); equivalent to clicking button on gui 

  Tab = Set secondary structure restraints to 'None'
    q = Set secondary structure restraints to 'Alpha helix'
    w = Set secondary structure restraints to 'Beta sheet'

    W = Flip peptide
    E = Kill active sidechain (stub)
    R = Real space refine in a 3.5A sphere
    F = Toggle fix atom on click (widget for fix atoms needs to be open for correct behavior)
    g = Go to blob under cursor
"""

## lower case key binds
# add_key_binding("Refine Active Residue", "r", lambda: manual_refine_residues(0))
add_key_binding("Set secondary structure restraints: None", "Tab", lambda: set_secondary_structure_restraints_type(0))
add_key_binding("Set secondary structure restraints: Alpha helix", "q", lambda: set_secondary_structure_restraints_type(1))
add_key_binding("Set secondary structure restraints: Beta strand", "w", lambda: set_secondary_structure_restraints_type(2))
add_key_binding("Real space refine zone", "r", lambda: do_refine(1))
add_key_binding("Regularize zone", "t", lambda: do_regularize(1))

## shift + key binds
add_key_binding("Pepflip", "W", lambda: pepflip_active_residue())
add_key_binding("Kill Sidechain", "E", lambda:
                using_active_atom(delete_residue_sidechain,
                                  "aa_imol", "aa_chain_id", "aa_res_no", "aa_ins_code", 0))

refine_residue_sphere_radius = 3.5  # Angstroms
add_key_binding("Refine residue in a sphere", "R",
                lambda: sphere_refine(refine_residue_sphere_radius))
add_key_binding("Fix atom", "F", lambda: setup_fixed_atom_pick(1,0))
add_key_binding("Go To Blob", "g", lambda: blob_under_pointer_to_screen_centre())
# add_key_binding("Add Water", "w", lambda: place_typed_atom_at_pointer("Water"))
# add_key_binding("Eigen-flip Ligand", "B", lambda: flip_active_ligand())
# add_key_binding("Undo", "a", lambda: apply_undo())
# add_key_binding("Redo", "z", lambda: apply_redo())

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



def key_binding_func_7():
    using_active_atom([[fit_to_map_by_random_jiggle,
                        ["aa_imol", "aa_chain_id", "aa_res_no", "aa_ins_code"],
                        [100, 1.0]]])
add_key_binding("Jiggle Fit", "J", lambda: key_binding_func_7())
