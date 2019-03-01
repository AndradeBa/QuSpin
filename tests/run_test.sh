
rm failed.txt

export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=4

for filename in *test.py
do
	python $filename
	if [ $? -ne 0 ]; then
		echo $filename"\n" >> failed.txt
		echo $filename"\n" >> ../failed.txt
	fi
done
