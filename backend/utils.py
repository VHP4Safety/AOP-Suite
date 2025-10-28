from bioregistry import get_iri

def convert_curie_to_iri(curie_or_namespace, local_id=None):
    """
    Convert CURIE to proper IRI using bioregistry.

    Args:
        curie_or_namespace: Either a full CURIE like "chebi:24867" or namespace like "chebi"
        local_id: Local identifier if namespace is provided

    Returns:
        str: Proper IRI URL or original string if conversion fails
    """
    try:
        if local_id:
            # Namespace and local_id provided separately
            return (
                get_iri(curie_or_namespace, local_id)
                or f"{curie_or_namespace}:{local_id}"
            )
        else:
            # Full CURIE provided
            if ":" in curie_or_namespace:
                namespace, lid = curie_or_namespace.split(":", 1)
                return get_iri(namespace, lid) or curie_or_namespace
            else:
                return curie_or_namespace
    except Exception as e:
        print(f"Error converting CURIE {curie_or_namespace}: {e}")
        return curie_or_namespace
