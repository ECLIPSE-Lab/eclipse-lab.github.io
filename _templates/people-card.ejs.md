```{=html}
<div class="people-grid list">
<% for (const item of items) {
     const key = String(item.path).replace(/[^a-zA-Z0-9_-]/g, "-");
     const panelId = `people-panel-${key}`;
     const summary = item.interests || item["card-bio"];
     const links = item.about && Array.isArray(item.about.links)
       ? item.about.links.filter(link => link && link.href)
       : [];
%>
  <article class="people-card" <%= metadataAttrs(item) %>>
    <a class="people-card__trigger" href="<%- item.path %>"
       aria-expanded="false" aria-controls="<%- panelId %>">
      <img class="people-card__portrait" src="<%- item.image %>"
           alt="<%- item.title %>" loading="lazy">
      <span class="people-card__name listing-title"><%- item.title %></span>
      <% if (item.subtitle) { %>
      <span class="people-card__role listing-subtitle"><%- item.subtitle %></span>
      <% } %>
    </a>
    <div class="people-card__panel" id="<%- panelId %>" aria-hidden="true">
      <% if (item.subtitle || item.started) { %>
      <div class="people-card__meta">
        <% if (item.subtitle) { %><strong><%- item.subtitle %></strong><% } %>
        <% if (item.started) { %><span>Since <%- item.started %></span><% } %>
      </div>
      <% } %>
      <% if (summary) { %>
      <div class="people-card__summary"><%- summary %></div>
      <% } %>
      <% if (links.length) { %>
      <div class="people-card__links">
        <% for (const link of links) { %>
        <a href="<%- link.href %>"><%- link.text || "Profile link" %></a>
        <% } %>
      </div>
      <% } %>
      <a class="people-card__profile-link" href="<%- item.path %>">View profile <span aria-hidden="true">→</span></a>
    </div>
  </article>
<% } %>
</div>
```
