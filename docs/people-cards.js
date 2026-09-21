(() => {
  document.documentElement.classList.add("people-cards-enhanced");

  const cards = [...document.querySelectorAll(".people-card")];
  if (!cards.length) return;

  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  let openCard = null;
  let restoringFocus = false;

  function keepPanelInViewport(card) {
    const panel = card.querySelector(".people-card__panel");
    panel.style.setProperty("--people-panel-shift", "0px");

    const rect = panel.getBoundingClientRect();
    const gutter = 16;
    let shift = 0;
    if (rect.left < gutter) shift += gutter - rect.left;
    if (rect.right > window.innerWidth - gutter) {
      shift -= rect.right - (window.innerWidth - gutter);
    }
    panel.style.setProperty("--people-panel-shift", `${shift}px`);
  }

  function setState(card, expanded) {
    const trigger = card.querySelector(".people-card__trigger");
    const panel = card.querySelector(".people-card__panel");

    card.classList.toggle("is-open", expanded);
    trigger.setAttribute("aria-expanded", String(expanded));
    panel.setAttribute("aria-hidden", String(!expanded));

    if (expanded) {
      openCard = card;
      window.requestAnimationFrame(() => keepPanelInViewport(card));
    } else {
      panel.style.removeProperty("--people-panel-shift");
      if (openCard === card) openCard = null;
    }
  }

  function closeCurrent(except = null) {
    if (openCard && openCard !== except) setState(openCard, false);
  }

  cards.forEach((card) => {
    const trigger = card.querySelector(".people-card__trigger");
    let coarseActivation = false;

    card.addEventListener("mouseenter", () => {
      closeCurrent(card);
      window.requestAnimationFrame(() => keepPanelInViewport(card));
    });

    trigger.addEventListener("pointerdown", (event) => {
      coarseActivation =
        event.pointerType === "touch" || event.pointerType === "pen";
    });

    trigger.addEventListener("focus", () => {
      if (coarseActivation || restoringFocus) return;
      closeCurrent(card);
      setState(card, true);
    });

    trigger.addEventListener("click", (event) => {
      const isCoarseClick = coarseActivation || !finePointer.matches;
      coarseActivation = false;
      if (!isCoarseClick || card.classList.contains("is-open")) return;

      event.preventDefault();
      closeCurrent(card);
      setState(card, true);
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;

      event.preventDefault();
      const expanded = trigger.getAttribute("aria-expanded") === "true";
      closeCurrent(card);
      setState(card, !expanded);
    });

    card.addEventListener("focusout", () => {
      window.requestAnimationFrame(() => {
        if (!card.contains(document.activeElement)) setState(card, false);
      });
    });
  });

  document.addEventListener("click", (event) => {
    if (openCard && !openCard.contains(event.target)) setState(openCard, false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !openCard) return;

    const card = openCard;
    const trigger = card.querySelector(".people-card__trigger");
    setState(card, false);
    restoringFocus = true;
    trigger.focus();
    restoringFocus = false;
  });

  window.addEventListener("resize", () => {
    if (openCard) {
      window.requestAnimationFrame(() => keepPanelInViewport(openCard));
    }
  });
})();
