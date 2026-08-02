# Cluster overlays

Each directory owns only the desired state for one cluster. Applications pull
upstream Helm charts directly and keep all environment-specific values in the
Argo CD `Application` (`spec.source.helm.valuesObject`). This prevents wrapper
charts from mixing reusable chart code with prod/test addresses and storage.

The first slice is `pi5b`. It deliberately contains no NFS server, static PV,
MetalLB pool, production secret, or reference to `192.168.1.5`.
