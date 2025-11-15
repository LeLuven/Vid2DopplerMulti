import torch

def get_gb(bytes_val):
    """Konvertiert Bytes in Gigabytes"""
    return round(bytes_val / 1024**3, 2)

if not torch.xpu.is_available():
    print("Fehler: Intel XPU (GPU) wurde nicht gefunden.")
    print("Stelle sicher, dass 'source /opt/intel/oneapi/setvars.sh' ausgeführt wurde.")
else:
    device = torch.device("xpu")
    print(f"Gerät gefunden: {torch.xpu.get_device_name(device)}")
    
    # 1. Eigenschaften abfragen (get_device_properties)
    props = torch.xpu.get_device_properties(device)
    total_mem_gb = get_gb(props.total_memory)
    print(f"\nEigenschaft 'total_memory': {total_mem_gb} GB")
    print(f"(Dies ist oft der gesamte System-RAM oder ein theoretisches Maximum)")

    # 2. Speicher-Info abfragen (mem_get_info)
    free_mem, total_mem_allocatable = torch.xpu.mem_get_info(device)
    total_alloc_gb = get_gb(total_mem_allocatable)
    free_alloc_gb = get_gb(free_mem)
    
    print(f"\nFür PyTorch verfügbar (mem_get_info):")
    print(f"  Insgesamt Zuweisbar: {total_alloc_gb} GB")
    print(f"  Davon Frei:          {free_alloc_gb} GB")