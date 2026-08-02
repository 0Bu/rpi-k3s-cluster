.PHONY: bootstrap-pi5b bootstrap-pi5b-local-path bootstrap-pi5c bootstrap-pi5c-local-path check status-pi5b status-pi5c

bootstrap-pi5b:
	./bootstrap/scripts/bootstrap-cluster.sh pi5b

bootstrap-pi5b-local-path:
	./bootstrap/scripts/bootstrap-cluster.sh pi5b --storage-backend local-path

bootstrap-pi5c:
	./bootstrap/scripts/bootstrap-cluster.sh pi5c

bootstrap-pi5c-local-path:
	./bootstrap/scripts/bootstrap-cluster.sh pi5c --storage-backend local-path

check:
	./bootstrap/scripts/check.sh

status-pi5b:
	KUBECONFIG=.state/pi5b/kubeconfig kubectl get nodes,applications.argoproj.io -A

status-pi5c:
	KUBECONFIG=.state/pi5c/kubeconfig kubectl get nodes,applications.argoproj.io -A
