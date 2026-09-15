(() => {
    "use strict";

    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;


    /* =========================================================
       CARD HOVER ENHANCEMENTS
       ========================================================= */

    function markHoverCards() {

        const selector = [
            ".quick-card",
            ".dashboard-card",
            ".product-card",
            ".sw-product-card",
            ".sw-restaurant-card",
            ".sw-menu-dish",
            ".in-service-card",
            ".in-project-card",
            ".card"
        ].join(",");

        document.querySelectorAll(selector).forEach((element) => {
            element.classList.add("proto-hoverable");
        });

    }


    /* =========================================================
       REVEAL ANIMATIONS
       ========================================================= */

    function addRevealMotion() {

        if (reducedMotion) {
            return;
        }

        const candidates = Array.from(
            document.querySelectorAll(
                [
                    "main .card",
                    "main .hero-panel",
                    "main .dashboard-card",
                    "main .chart-card",
                    "main .metric-card",
                    "main .stat-card",
                    "main .sw-restaurant-card",
                    "main .sw-product-card",
                    "main .sw-menu-dish",
                    "main .sw-order-card",
                    "main .in-service-card",
                    "main .in-project-card",
                    ".merchant-main .card",
                    ".merchant-main [class*='card']",
                    ".merchant-main [class*='panel']"
                ].join(",")
            )
        ).filter(
            (element, index, collection) =>
                collection.indexOf(element) === index
        );

        candidates
            .slice(0, 80)
            .forEach((element, index) => {

                element.classList.add("proto-reveal");

                element.style.setProperty(
                    "--proto-delay",
                    `${Math.min(index % 8, 7) * 36}ms`
                );

            });

        const observer = new IntersectionObserver(
            (entries) => {

                entries.forEach((entry) => {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.classList.add("proto-visible");

                    observer.unobserve(entry.target);

                });

            },
            {
                rootMargin: "0px 0px -8% 0px",
                threshold: 0.04
            }
        );

        candidates.forEach((element) => {
            observer.observe(element);
        });

    }


    /* =========================================================
       BUTTON PRESS ANIMATION
       ========================================================= */

    function addButtonPressMotion() {

        document.addEventListener(
            "pointerdown",
            (event) => {

                const button = event.target.closest(
                    "button, .btn, [role='button']"
                );

                if (
                    !button ||
                    button.matches(
                        ":disabled, [aria-disabled='true']"
                    )
                ) {
                    return;
                }

                button.classList.add("proto-pressed");

            },
            {
                passive: true
            }
        );


        const clear = () => {

            document
                .querySelectorAll(".proto-pressed")
                .forEach((button) => {

                    button.classList.remove(
                        "proto-pressed"
                    );

                });

        };


        document.addEventListener(
            "pointerup",
            clear,
            {
                passive: true
            }
        );


        document.addEventListener(
            "pointercancel",
            clear,
            {
                passive: true
            }
        );

    }


    /* =========================================================
       COUNTER / BADGE POP ANIMATION
       ========================================================= */

    function addCounterMotion() {

        const selectors = [
            ".sw-cart-count",
            ".cart-count",
            ".badge-count",
            "[data-cart-count]",
            "[data-notification-count]"
        ];


        document
            .querySelectorAll(
                selectors.join(",")
            )
            .forEach((badge) => {

                const observer =
                    new MutationObserver(() => {

                        badge.classList.remove(
                            "proto-count-pop"
                        );

                        void badge.offsetWidth;

                        badge.classList.add(
                            "proto-count-pop"
                        );

                    });


                observer.observe(
                    badge,
                    {
                        childList: true,
                        characterData: true,
                        subtree: true
                    }
                );

            });

    }


    /* =========================================================
       THEME TOGGLE ANIMATION
       ========================================================= */

    function addThemeMotion() {

        const themeButtons =
            document.querySelectorAll(
                [
                    "#themeToggle",
                    "#theme-toggle",
                    "[data-theme-toggle]",
                    ".theme-toggle"
                ].join(",")
            );


        const htmlObserver =
            new MutationObserver(
                (mutations) => {

                    if (
                        !mutations.some(
                            (mutation) =>
                                mutation.attributeName ===
                                "data-bs-theme"
                        )
                    ) {
                        return;
                    }


                    themeButtons.forEach(
                        (button) => {

                            button.classList.remove(
                                "proto-theme-spin"
                            );

                            void button.offsetWidth;

                            button.classList.add(
                                "proto-theme-spin"
                            );

                        }
                    );

                }
            );


        htmlObserver.observe(
            document.documentElement,
            {
                attributes: true,
                attributeFilter: [
                    "data-bs-theme"
                ]
            }
        );

    }


    /* =========================================================
       LIVE STATUS INDICATOR
       ========================================================= */

    function addLiveCue() {

        const possibleLiveAreas =
            document.querySelectorAll(
                [
                    ".merchant-topbar-title",
                    ".dashboard-header",
                    ".page-header",
                    ".sw-preview-nav-status"
                ].join(",")
            );


        possibleLiveAreas.forEach((area) => {

            if (
                area.querySelector(
                    ".proto-live-dot"
                )
            ) {
                return;
            }


            const text =
                (
                    area.textContent || ""
                ).toLowerCase();


            if (
                !/(live|order|dashboard|operations|preview)/
                    .test(text)
            ) {
                return;
            }


            const dot =
                document.createElement(
                    "span"
                );


            dot.className =
                "proto-live-dot";


            dot.setAttribute(
                "aria-hidden",
                "true"
            );


            dot.style.marginInlineEnd =
                "7px";


            const target =
                area.querySelector(
                    "small, .eyebrow"
                ) ||
                area.firstElementChild;


            if (target) {
                target.prepend(dot);
            }

        });

    }


    /* =========================================================
       FORM LOADING FEEDBACK
       ========================================================= */

    function addLoadingFeedback() {

        document.addEventListener(
            "submit",
            (event) => {

                const form =
                    event.target;


                if (
                    !(
                        form instanceof
                        HTMLFormElement
                    )
                ) {
                    return;
                }


                const submitter =
                    event.submitter;


                if (
                    !submitter ||
                    !submitter.matches(
                        "button, input[type='submit']"
                    )
                ) {
                    return;
                }


                if (
                    form.hasAttribute(
                        "data-no-proto-loading"
                    )
                ) {
                    return;
                }


                submitter.classList.add(
                    "proto-shimmer"
                );


                /*
                 * Existing page JavaScript still owns
                 * disabled/loading states.
                 *
                 * This UI layer only provides the
                 * visual shimmer.
                 */

                window.setTimeout(
                    () => {

                        if (
                            document.contains(
                                submitter
                            )
                        ) {

                            submitter.classList.remove(
                                "proto-shimmer"
                            );

                        }

                    },
                    2600
                );

            }
        );

    }


    /* =========================================================
       ADMIN TABLE PAGINATION
       ========================================================= */

    function addAdminTablePagination() {

        const path =
            window.location.pathname
                .replace(/\/+$/, "") || "/";


        /*
         * Pagination configuration.
         *
         * Each page keeps its existing HTML,
         * search logic and backend routes.
         *
         * Pagination is applied only in the
         * browser.
         */

        const routeConfig = {

            "/products": {
                tableSelector: "section table",
                rowSelector:
                    "tbody > tr.catalog-row"
            },

            "/admin/restaurants": {
                tableSelector:
                    ".table-responsive table",
                rowSelector:
                    "tbody > tr"
            },

            "/admin/users": {
                tableSelector:
                    ".table-responsive table",
                rowSelector:
                    "tbody > tr"
            },

            "/admin/merchants": {
                tableSelector:
                    ".table-responsive table",
                rowSelector:
                    "tbody > tr[data-merchant-row]"
            }

        };


        const config =
            routeConfig[path];


        if (!config) {
            return;
        }


        const tables =
            Array.from(
                document.querySelectorAll(
                    config.tableSelector
                )
            );


        if (!tables.length) {
            return;
        }


        const paginators = [];


        tables.forEach(
            (table, tableIndex) => {


                /*
                 * Prevent initialization twice.
                 */

                if (
                    table.dataset
                        .adminPaginationReady ===
                    "true"
                ) {
                    return;
                }


                /*
                 * Empty-state rows usually have
                 * colspan attributes.
                 *
                 * We do not paginate those.
                 */

                const rows =
                    Array.from(
                        table.querySelectorAll(
                            config.rowSelector
                        )
                    ).filter(
                        (row) =>
                            !row.querySelector(
                                "td[colspan]"
                            )
                    );


                if (!rows.length) {
                    return;
                }


                table.dataset
                    .adminPaginationReady =
                    "true";


                let currentPage = 1;

                let pageSize = 10;


                /* =============================================
                   PAGINATION WRAPPER
                   ============================================= */

                const footer =
                    document.createElement(
                        "div"
                    );


                footer.className =
                    "admin-table-pagination";


                footer.dataset.tableIndex =
                    String(tableIndex);


                /* =============================================
                   PAGINATION INFORMATION
                   ============================================= */

                const meta =
                    document.createElement(
                        "div"
                    );


                meta.className =
                    "admin-table-pagination__meta";


                const info =
                    document.createElement(
                        "span"
                    );


                info.setAttribute(
                    "aria-live",
                    "polite"
                );


                /* =============================================
                   ROW COUNT SELECTOR
                   ============================================= */

                const sizeWrap =
                    document.createElement(
                        "label"
                    );


                sizeWrap.className =
                    "admin-table-pagination__size";


                sizeWrap.append(
                    document.createTextNode(
                        "Rows"
                    )
                );


                const sizeSelect =
                    document.createElement(
                        "select"
                    );


                sizeSelect.setAttribute(
                    "aria-label",
                    "Rows per page"
                );


                [
                    10,
                    25,
                    50
                ].forEach(
                    (value) => {

                        const option =
                            document.createElement(
                                "option"
                            );


                        option.value =
                            String(value);


                        option.textContent =
                            String(value);


                        option.selected =
                            value === pageSize;


                        sizeSelect.append(
                            option
                        );

                    }
                );


                sizeWrap.append(
                    sizeSelect
                );


                meta.append(
                    info,
                    sizeWrap
                );


                /* =============================================
                   PAGE BUTTON CONTAINER
                   ============================================= */

                const controls =
                    document.createElement(
                        "div"
                    );


                controls.className =
                    "admin-table-pagination__controls";


                controls.setAttribute(
                    "aria-label",
                    "Table pagination"
                );


                footer.append(
                    meta,
                    controls
                );


                /* =============================================
                   INSERT PAGINATION UNDER TABLE
                   ============================================= */

                const responsive =
                    table.closest(
                        ".table-responsive"
                    );


                if (responsive) {

                    responsive
                        .insertAdjacentElement(
                            "afterend",
                            footer
                        );

                } else {

                    table
                        .insertAdjacentElement(
                            "afterend",
                            footer
                        );

                }


                /* =============================================
                   EXISTING SEARCH FILTER SUPPORT
                   ============================================= */

                function isFilteredIn(row) {

                    /*
                     * Catalog search currently hides
                     * rows using inline display:none.
                     */

                    if (
                        row.style.display ===
                        "none"
                    ) {
                        return false;
                    }


                    /*
                     * Merchant search uses Bootstrap
                     * d-none.
                     */

                    if (
                        row.classList.contains(
                            "d-none"
                        )
                    ) {
                        return false;
                    }


                    return true;

                }


                /* =============================================
                   CREATE PAGINATION BUTTON
                   ============================================= */

                function makeButton(
                    label,
                    options = {}
                ) {

                    const button =
                        document.createElement(
                            "button"
                        );


                    button.type =
                        "button";


                    button.className =
                        "admin-table-pagination__button";


                    button.textContent =
                        label;


                    if (
                        options.active
                    ) {

                        button.classList.add(
                            "is-active"
                        );


                        button.setAttribute(
                            "aria-current",
                            "page"
                        );

                    }


                    button.disabled =
                        Boolean(
                            options.disabled
                        );


                    if (
                        options.ariaLabel
                    ) {

                        button.setAttribute(
                            "aria-label",
                            options.ariaLabel
                        );

                    }


                    if (
                        typeof options.onClick ===
                        "function"
                    ) {

                        button.addEventListener(
                            "click",
                            options.onClick
                        );

                    }


                    return button;

                }


                /* =============================================
                   PAGE NUMBER LIST
                   ============================================= */

                function buildPageList(
                    totalPages
                ) {

                    /*
                     * Small result sets show every
                     * page number.
                     */

                    if (
                        totalPages <= 7
                    ) {

                        return Array.from(
                            {
                                length:
                                    totalPages
                            },
                            (
                                _,
                                index
                            ) =>
                                index + 1
                        );

                    }


                    /*
                     * Larger result sets use
                     * ellipses:
                     *
                     * 1 ... 4 5 6 ... 12
                     */

                    const pages =
                        [1];


                    const windowStart =
                        Math.max(
                            2,
                            currentPage - 1
                        );


                    const windowEnd =
                        Math.min(
                            totalPages - 1,
                            currentPage + 1
                        );


                    if (
                        windowStart > 2
                    ) {

                        pages.push(
                            "ellipsis-start"
                        );

                    }


                    for (
                        let page =
                            windowStart;
                        page <=
                            windowEnd;
                        page += 1
                    ) {

                        pages.push(
                            page
                        );

                    }


                    if (
                        windowEnd <
                        totalPages - 1
                    ) {

                        pages.push(
                            "ellipsis-end"
                        );

                    }


                    pages.push(
                        totalPages
                    );


                    return pages;

                }


                /* =============================================
                   RENDER PAGINATION
                   ============================================= */

                function render(
                    {
                        reset = false
                    } = {}
                ) {

                    /*
                     * Searching should always bring
                     * the user back to page 1.
                     */

                    if (reset) {
                        currentPage = 1;
                    }


                    /*
                     * Only paginate rows that still
                     * pass the page's existing search.
                     */

                    const eligibleRows =
                        rows.filter(
                            isFilteredIn
                        );


                    const totalRows =
                        eligibleRows.length;


                    const totalPages =
                        Math.max(
                            1,
                            Math.ceil(
                                totalRows /
                                pageSize
                            )
                        );


                    /*
                     * Handle removing/searching rows
                     * while currently on a later page.
                     */

                    if (
                        currentPage >
                        totalPages
                    ) {

                        currentPage =
                            totalPages;

                    }


                    const startIndex =
                        (
                            currentPage - 1
                        ) *
                        pageSize;


                    const endIndex =
                        Math.min(
                            startIndex +
                                pageSize,
                            totalRows
                        );


                    /*
                     * Clear only pagination visibility.
                     *
                     * Search visibility remains untouched.
                     */

                    rows.forEach(
                        (row) => {

                            row.classList.remove(
                                "admin-pagination-hidden"
                            );

                        }
                    );


                    /*
                     * Hide all rows outside the
                     * current page.
                     */

                    eligibleRows.forEach(
                        (
                            row,
                            index
                        ) => {

                            const shouldHide =
                                index <
                                    startIndex ||
                                index >=
                                    endIndex;


                            row.classList.toggle(
                                "admin-pagination-hidden",
                                shouldHide
                            );

                        }
                    );


                    /* =========================================
                       INFORMATION TEXT
                       ========================================= */

                    if (
                        totalRows === 0
                    ) {

                        info.textContent =
                            "0 results";

                    } else {

                        info.textContent =
                            `Showing ${
                                startIndex + 1
                            }–${endIndex} of ${totalRows}`;

                    }


                    /* =========================================
                       PAGE CONTROLS
                       ========================================= */

                    controls.replaceChildren();


                    /*
                     * Previous button
                     */

                    controls.append(
                        makeButton(
                            "‹",
                            {

                                disabled:
                                    currentPage <=
                                        1 ||
                                    totalRows ===
                                        0,

                                ariaLabel:
                                    "Previous page",

                                onClick:
                                    () => {

                                        if (
                                            currentPage >
                                            1
                                        ) {

                                            currentPage -=
                                                1;

                                            render();

                                        }

                                    }

                            }
                        )
                    );


                    /*
                     * Page numbers
                     */

                    buildPageList(
                        totalPages
                    ).forEach(
                        (page) => {

                            if (
                                typeof page !==
                                "number"
                            ) {

                                const ellipsis =
                                    document.createElement(
                                        "span"
                                    );


                                ellipsis.className =
                                    "admin-table-pagination__ellipsis";


                                ellipsis.textContent =
                                    "…";


                                controls.append(
                                    ellipsis
                                );


                                return;

                            }


                            controls.append(
                                makeButton(
                                    String(
                                        page
                                    ),
                                    {

                                        active:
                                            page ===
                                            currentPage,

                                        ariaLabel:
                                            `Page ${page}`,

                                        onClick:
                                            () => {

                                                currentPage =
                                                    page;

                                                render();

                                            }

                                    }
                                )
                            );

                        }
                    );


                    /*
                     * Next button
                     */

                    controls.append(
                        makeButton(
                            "›",
                            {

                                disabled:
                                    currentPage >=
                                        totalPages ||
                                    totalRows ===
                                        0,

                                ariaLabel:
                                    "Next page",

                                onClick:
                                    () => {

                                        if (
                                            currentPage <
                                            totalPages
                                        ) {

                                            currentPage +=
                                                1;

                                            render();

                                        }

                                    }

                            }
                        )
                    );

                }


                /* =============================================
                   ROWS PER PAGE CHANGE
                   ============================================= */

                sizeSelect.addEventListener(
                    "change",
                    () => {

                        pageSize =
                            Number.parseInt(
                                sizeSelect.value,
                                10
                            ) ||
                            10;


                        currentPage =
                            1;


                        render();

                    }
                );


                paginators.push(
                    {
                        table,
                        render
                    }
                );


                /*
                 * Initial table render.
                 */

                render();

            }
        );


        if (
            !paginators.length
        ) {
            return;
        }


        /* =====================================================
           SYNCHRONIZE WITH EXISTING SEARCH FIELDS
           ===================================================== */

        /*
         * Catalog and merchant pages already
         * own their own search behavior.
         *
         * We simply refresh pagination after
         * their filters have changed row visibility.
         */

        const refreshAfterFilter =
            (event) => {

                const target =
                    event.target;


                if (
                    !(
                        target instanceof
                        Element
                    )
                ) {
                    return;
                }


                if (
                    !target.matches(
                        "#catalog-search, " +
                        "#merchant-search, " +
                        "#catalog-search-clear"
                    )
                ) {
                    return;
                }


                window.requestAnimationFrame(
                    () => {

                        paginators.forEach(
                            (paginator) => {

                                paginator.render(
                                    {
                                        reset:
                                            true
                                    }
                                );

                            }
                        );

                    }
                );

            };


        document.addEventListener(
            "input",
            refreshAfterFilter
        );


        document.addEventListener(
            "click",
            refreshAfterFilter
        );

    }


    /* =========================================================
       INITIALIZE PROTOTYPE UI
       ========================================================= */

    function init() {

        document.body.classList.add(
            "prototype-b-merged-ui"
        );


        markHoverCards();

        addRevealMotion();

        addButtonPressMotion();

        addCounterMotion();

        addThemeMotion();

        addLiveCue();

        addLoadingFeedback();

        addAdminTablePagination();

    }


    /* =========================================================
       DOM READY
       ========================================================= */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            init,
            {
                once: true
            }
        );

    } else {

        init();

    }

})();