---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: plain
---

# Formalized theorems

<table class="display datatable" data-order-columns="[1]">
    <thead>
        <tr>
            <th class="dt-head-center">MSC</th>
            <th>Name</th>
            <th class="dt-head-center">Isabelle</th>
            <th class="dt-head-center">HOL Light</th>
            <th class="dt-head-center">Coq/Rocq</th>
            <th class="dt-head-center">Lean</th>
            <th class="dt-head-center">Metamath</th>
            <th class="dt-head-center">Mizar</th>
        </tr>
    </thead>
    <tbody>
        {% assign sorted = site.thm | sort: "wikidata" %}
        {% for t in sorted %}
            {% if t.isabelle or t.hol_light or t.rocq or t.lean or t.metamath or t.mizar %}
            <tr>
                <td class="dt-body-center"><span title="{{ site.data.msc[t.msc_classification] }}">{{ t.msc_classification }}</span></td>
                <td>
                    {% assign wl = t.wikipedia_links.first %}
                    {% if wl contains "|" %}
                        {% assign wl_parts = wl | split: '|' %}
                        {% assign wlabel = wl_parts[1] | remove: ']]' %}
                        {% assign wurl = wl_parts[0] | remove: '[[' %}
                    {% else %}
                        {% assign wlabel = wl | remove: '[[' | remove: ']]' %}
                        {% assign wurl = wlabel %}
                    {% endif %}
                    <a href="https://en.wikipedia.org/wiki/{{ wurl }}">{{ wlabel }}</a>
                </td>
                <td class="dt-body-center"></td>
                <td class="dt-body-center"></td>
                <td class="dt-body-center"></td>
                <td class="dt-body-center">
                    {% if t.lean %}
                        {% for f in t.lean %}
                            <a href="{{ f.url }}" title="{{ f.authors | join: ', ' }}">{{ f.library }}</a>
                        {% endfor %}
                    {% endif %}
                </td>
                <td class="dt-body-center"></td>
                <td class="dt-body-center"></td>
            </tr>
            {% endif %}
        {% endfor %}
    </tbody>
</table>
