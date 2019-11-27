docker exec -it hadoop-master python2 get-pip.py
docker exec -it hadoop-master python2 -m pip install ipykernel
# above line automatically installs a wrong "python2" kernel
docker exec -it hadoop-master jupyter kernelspec uninstall python2
# more convenient to put requirements.txt in dags folder lol
docker exec -it hadoop-master python2 -m pip install -r dags/requirements.txt
docker exec -it --user hadoop hadoop-master python2 -m ipykernel install --user --name finnet-pipeline --display-name "finnet-pipeline (Python 2)"

