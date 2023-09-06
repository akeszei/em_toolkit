echo "Run this script as sudo for it to properly work!"

## Remove all projects
if [ -d "em_dataset_curator" ]; then
    rm -r em_dataset_curator
fi

if [ -d "em_image_conversion" ]; then
    rm -r em_image_conversion
fi

if [ -d "em_toolkit" ]; then
    rm -r em_toolkit
fi

if [ -d "bash_toolkit" ]; then
    rm -r bash_toolkit
fi


## Pull fresh projects from repo
git clone https://github.com/akeszei/em_image_conversion
git clone https://github.com/akeszei/em_dataset_curator
git clone https://github.com/akeszei/em_toolkit

## Make specific scripts executable
chmod +x em_dataset_curator/em_dataset_curator.py
chmod +x em_dataset_curator/marked_imgs_to_backup_selection.py
chmod +x em_image_conversion/em_header.py
chmod +x em_image_conversion/mrc2img.py
chmod +x em_image_conversion/ser2mrc.py
chmod +x em_image_conversion/ser2img.py
chmod +x em_image_conversion/mrcs_viewer.py
chmod +x em_image_conversion/mrc_viewer.py
chmod +x em_image_conversion/stack_mrc.py
chmod +x em_toolkit/cs_file_tools/get_particle_locations_from_cs.py
chmod +x em_toolkit/cs_file_tools/read_cs.py
chmod +x em_toolkit/star_file_tools/class3D_statistics.py
chmod +x em_toolkit/star_file_tools/display_class2D.py
chmod +x em_toolkit/star_file_tools/remap_optics_groups.py
chmod +x em_toolkit/star_file_tools/remap_optics_groups_by_inputfile.py
chmod +x em_toolkit/star_file_tools/remove_mics_from_star.py
chmod +x em_toolkit/star_file_tools/select_into_manpick.py
chmod +x em_toolkit/star_file_tools/merge_star_coordinates.py
chmod +x em_toolkit/star_file_tools/plot_fsc.py
chmod +x em_toolkit/EPU_tools/show_atlas_position.py
chmod +x em_toolkit/EPU_tools/EPU_assign_tiltgroups.py
chmod +x em_toolkit/EPU_tools/EPU_reorganize_krios_data.sh
chmod +x em_toolkit/EPU_tools/EPU_reorganize_talos_data.sh
chmod +x em_toolkit/EPU_tools/EPU_array_atlas_jpgs.py
chmod +x em_toolkit/bash_tools/add_dummy_picks_to_missing_mics.sh
chmod +x em_toolkit/bash_tools/link_data.sh
chmod +x em_toolkit/bash_tools/get_random_subset_list_from_files.sh
chmod +x em_toolkit/bash_tools/link_mics_from_file.sh
chmod +x em_toolkit/bash_tools/compare_dirs.sh

## Add link for each executable into a common binaries folder for loading onto $PATH
if [ -d "bin" ]; then
    rm -r bin
fi

mkdir bin
ln -s ../em_dataset_curator/em_dataset_curator.py bin/
ln -s ../em_dataset_curator/marked_imgs_to_backup_selection.py bin/
ln -s ../em_image_conversion/em_header.py bin/
ln -s ../em_image_conversion/mrc2img.py bin/
ln -s ../em_image_conversion/ser2mrc.py bin/
ln -s ../em_image_conversion/ser2img.py bin/
ln -s ../em_image_conversion/mrcs_viewer.py bin/
ln -s ../em_image_conversion/mrc_viewer.py bin/
ln -s ../em_image_conversion/stack_mrc.py bin/
ln -s ../em_toolkit/cs_file_tools/get_particle_locations_from_cs.py bin/
ln -s ../em_toolkit/cs_file_tools/read_cs.py bin/
ln -s ../em_toolkit/star_file_tools/class3D_statistics.py bin/
ln -s ../em_toolkit/star_file_tools/display_class2D.py bin/
ln -s ../em_toolkit/star_file_tools/remap_optics_groups.py bin/
ln -s ../em_toolkit/star_file_tools/remap_optics_groups_by_inputfile.py bin/
ln -s ../em_toolkit/star_file_tools/remove_mics_from_star.py bin/
ln -s ../em_toolkit/star_file_tools/select_into_manpick.py bin/
ln -s ../em_toolkit/star_file_tools/merge_star_coordinates.py bin/
ln -s ../em_toolkit/star_file_tools/plot_fsc.py bin/
ln -s ../em_toolkit/EPU_tools/show_atlas_position.py bin/
ln -s ../em_toolkit/EPU_tools/EPU_assign_tiltgroups.py bin/
ln -s ../em_toolkit/EPU_tools/EPU_reorganize_krios_data.sh bin/
ln -s ../em_toolkit/EPU_tools/EPU_reorganize_talos_data.sh bin/
ln -s ../em_toolkit/EPU_tools/EPU_array_atlas_jpgs.py bin/
