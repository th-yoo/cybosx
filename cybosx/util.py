def singletonize(inst):
    def get_instance():
        nonlocal inst
        return inst
    return get_instance

