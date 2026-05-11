from django import template

register = template.Library()

ALWAYS_EXCLUDE = {
    "id",
    "product_group",
    "group_slug",
    "note_for_manager",
    "created_at",
    "updated_at",
    "is_available",
    "is_hit",
    "popularity",
    "stock",
}


@register.filter
def get_visible_fields(obj, exclude_fields=None):
    if exclude_fields:
        exclude_list = [f.strip() for f in exclude_fields.split(",")]
    else:
        exclude_list = []

    fields = []
    for field in obj._meta.get_fields():
        if (
            hasattr(field, "verbose_name")
            and hasattr(field, "name")
            and field.name not in ALWAYS_EXCLUDE  # ← всегда исключаем
            and field.name not in exclude_list  # ← исключаем из шаблона
            and not field.auto_created
            and not field.is_relation
        ):
            fields.append(
                {
                    "name": field.name,
                    "verbose_name": str(field.verbose_name),
                    "value": getattr(obj, field.name),
                    "field_type": field.get_internal_type(),
                    "is_empty": getattr(obj, field.name) in (None, "", 0, [], {}),
                }
            )
    return fields
