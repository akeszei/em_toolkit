## Assign number of working threads
N=12

## Create the task for each individual unit of work 
task(){
   input_mrcs=$1
   bg_radius=84
   echo relion_preprocess --operate_on $input_mrcs --operate_out out/$input_mrcs --norm --float16 --bg_radius $bg_radius
}

## Prepare the list of working elements via globbing and pass them through a iterator with background execution in batches 
(
   for job in *.mrcs ; do 
      
      ## create batches on-the-fly using a variable initialized at 0 and execute them in the background, adding the wait command on the first operation, thus restricting the run until all its children threads are done 
      ((i=i%N)); ((i++==0)) && wait 

      ## launch a job for the input file in the background 
      task "$job" & 

   done
)