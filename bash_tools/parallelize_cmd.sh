N=4

task(){
   sleep $1; echo " >> $1";
}


(
for thing in 3 3 2 1 1 2 3 3 ; do 
   ((i=i%N)); ((i++==0)) && wait
   task "$thing" & 
done
)
