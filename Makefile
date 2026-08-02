.PHONY: bootstrap-pi5b check status-pi5b

bootstrap-pi5b:
	./bootstrap/scripts/bootstrap-cluster.sh pi5b

check:
	./bootstrap/scripts/check.sh

status-pi5b:
	KUBECONFIG=.state/pi5b/kubeconfig kubectl get nodes,applications.argoproj.io -A
