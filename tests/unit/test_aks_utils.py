from reco_utils.azureml.aks_utils import qps_to_replicas, replicas_to_qps, total_cores_to_replicas

def test_qps_to_replicas():
    replicas = qps_to_replicas(target_qps=25, processing_time=0.1)
    assert replicas == 4

def test_replicas_to_qps():
    qps = replicas_to_qps(num_replicas=4, processing_time=0.1)
    assert qps == 27

def test_total_cores_to_replicas():
    max_replicas = total_cores_to_replicas(12, cpu_cores_per_replica=0.1)
    assert max_replicas == 108
