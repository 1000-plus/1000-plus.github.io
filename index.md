---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: plain
---

# Theorems with at least one formalization

<table class="display datatable" data-order-columns="[1]">
    <thead>
        <tr>
            <th>WikidataID</th>
            <th>Name</th>
            <th>Isabelle</th>
            <th>HOL Light</th>
            <th>Coq</th>
            <th>Lean</th>
            <th>Metamath</th>
            <th>Mizar</th>
        </tr>
    </thead>
    <tbody>
        {% assign sorted = site.thm | sort: "wikidata" %}
        {% for t in sorted %}
            {% if t.isabelle or t.hol_light or t.coq or t.lean or t.metamath or t.mizar %}
            <tr>
                <td>{{ t.wikidata }}</td>
                <td>
                    {% assign wl = t.wikipedia_links.first %}
                    {% if wl contains "|" %}
                        {% assign wl_parts = wl | split: '|' %}
                        {{ wl_parts[1] | remove: ']]' }}
                    {% else %}
                        {{ wl | remove: '[[' | remove: ']]' }}
                    {% endif %}
                </td>
                <td></td>
                <td></td>
                <td></td>
                <td>
                    {% if t.lean %}
                        {% for f in t.lean %}
                            <a href="{{ f.url }}">{{ f.library }}</a>
                        {% endfor %}
                    {% endif %}
                </td>
                <td></td>
                <td></td>
            </tr>
            {% endif %}
        {% endfor %}
    </tbody>
</table>
