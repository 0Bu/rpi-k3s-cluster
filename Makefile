.PHONY: bootstrap-pi5b bootstrap-pi5b-local-path check status-pi5b

bootstrap-pi5b:
	./bootstrap/scripts/bootstrap-cluster.sh pi5b

bootstrap-pi5b-local-path:
	./bootstrap/scripts/bootstrap-cluster.sh pi5b --storage-backend local-path

check:
	./bootstrap/scripts/check.sh

status-pi5b:
	KUBECONFIG=.state/pi5b/kubeconfig kubectl get nodes,applications.argoproj.io -A
