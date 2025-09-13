class ValidationError(Exception):
    def __init__(self, message, path=None):
        super().__init__(message)
        self.message = message
        self.path = list(path or [])

def _check_type(instance, typ):
    if typ == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if typ == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if typ == "string":
        return isinstance(instance, str)
    if typ == "object":
        return isinstance(instance, dict)
    if typ == "array":
        return isinstance(instance, list)
    if typ == "null":
        return instance is None
    return True

def _iter_errors(instance, schema, path):
    typ = schema.get("type")
    if isinstance(typ, list):
        if not any(_check_type(instance, t) for t in typ):
            yield ValidationError(f"expected type {typ}", path)
            return
        for t in typ:
            if _check_type(instance, t):
                typ = t
                break
    elif typ and not _check_type(instance, typ):
        yield ValidationError(f"expected type {typ}", path)
        return
    if typ == "object":
        if not isinstance(instance, dict):
            return
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                yield ValidationError(f"'{key}' is required", path + [key])
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                yield from _iter_errors(value, props[key], path + [key])
            elif additional is False:
                yield ValidationError("additional property not allowed", path + [key])
    elif typ == "array":
        if not isinstance(instance, list):
            return
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(instance) < min_items:
            yield ValidationError(f"minItems is {min_items}", path)
        if max_items is not None and len(instance) > max_items:
            yield ValidationError(f"maxItems is {max_items}", path)
        items_schema = schema.get("items")
        if items_schema:
            for idx, item in enumerate(instance):
                yield from _iter_errors(item, items_schema, path + [idx])
    else:
        pass

class Draft7Validator:
    def __init__(self, schema):
        self.schema = schema
    def iter_errors(self, instance):
        return _iter_errors(instance, self.schema, [])
