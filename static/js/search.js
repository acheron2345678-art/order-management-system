(() => {

    let timer;


    function escapeHtml(value) {

        const div =
            document.createElement("div");

        div.textContent =
            value ?? "";

        return div.innerHTML;

    }


    function detailUrl(
        platform,
        id
    ) {

        const role =
            document.body
                ?.dataset
                ?.userRole
            ||
            "";


        if (
            role
            ===
            "client"
        ) {

            if (
                platform
                ===
                "swiggy"
            ) {

                return (
                    `/swiggy/my-orders/${id}`
                );

            }


            if (
                platform
                ===
                "insights"
            ) {

                return (
                    `/insights/my-projects/${id}`
                );

            }

        }


        return (
            `/${platform}/orders/view/${id}`
        );

    }


    function hideResults(results) {

        results.innerHTML = "";

        results.classList.remove(
            "show"
        );

    }


    function renderResults(
        resultsElement,
        orders
    ) {

        resultsElement.innerHTML = "";


        if (
            !orders
            ||
            orders.length === 0
        ) {

            resultsElement.innerHTML =
                '<div class="search-empty">No orders or projects found</div>';

            resultsElement.classList.add(
                "show"
            );

            return;

        }


        orders
            .slice(0, 10)
            .forEach(
                (order) => {

                    const platform =
                        String(
                            order.platform || ""
                        ).toLowerCase();


                    if (
                        ![
                            "swiggy",
                            "insights"
                        ].includes(platform)
                    ) {
                        return;
                    }


                    const item =
                        document.createElement(
                            "a"
                        );


                    item.className =
                        "search-result-item text-decoration-none";


                    item.href =
                        detailUrl(
                            platform,
                            order.id
                        );


                    const productName =
                        order.product_name
                            ? escapeHtml(
                                order.product_name
                            )
                            : "";


                    const productText =
                        productName
                            ? ` · ${productName}`
                            : "";


                    const recordLabel =
                        platform
                        ===
                        "insights"
                            ?
                            "Project"
                            :
                            "Order";


                    const clientUsername =
                        order.client_username
                            ? escapeHtml(
                                order.client_username
                            )
                            : "Unassigned";


                    const clientEmail =
                        order.client_email
                            ? escapeHtml(
                                order.client_email
                            )
                            : "";


                    const clientText =
                        clientEmail
                            ? `${clientUsername} · ${clientEmail}`
                            : clientUsername;


                    item.innerHTML = `

                        <span
                            class="platform-dot platform-${platform}"
                        >
                            ${
                                platform === "swiggy"
                                    ? "S"
                                    : "I"
                            }
                        </span>


                        <span class="search-result-copy">

                            <strong>
                                ${escapeHtml(
                                    order.customer_name
                                )}
                            </strong>


                            <small
                                class="d-block text-body-secondary"
                            >
                                Client:
                                ${clientText}
                            </small>


                            <small>

                                ${recordLabel}:
                                ${escapeHtml(
                                    order.order_number
                                )}

                                ${productText}

                                · ${escapeHtml(
                                    order.platform
                                )}

                                · ${escapeHtml(
                                    order.order_date
                                )}

                            </small>

                        </span>


                        <span class="search-result-end">

                            <span
                                class="status-badge status-${escapeHtml(
                                    order.status
                                )}"
                            >

                                ${escapeHtml(
                                    order.status
                                )}

                            </span>


                            <small>

                                ₹${Number(
                                    order.amount || 0
                                ).toLocaleString(
                                    "en-IN",
                                    {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    }
                                )}

                            </small>

                        </span>

                    `;


                    resultsElement.appendChild(
                        item
                    );

                }
            );


        resultsElement.classList.add(
            "show"
        );

    }


    async function performSearch(
        query,
        resultsElement
    ) {

        try {

            const response =
                await fetch(
                    `/search?q=${encodeURIComponent(
                        query
                    )}`
                );


            if (!response.ok) {

                throw new Error(
                    "Search request failed"
                );

            }


            const orders =
                await response.json();


            renderResults(
                resultsElement,
                orders
            );

        }

        catch (error) {

            console.error(
                "Universal search error:",
                error
            );


            resultsElement.innerHTML =
                '<div class="search-empty">Unable to perform search</div>';


            resultsElement.classList.add(
                "show"
            );

        }

    }


    document.addEventListener(
        "DOMContentLoaded",
        () => {

            const input =
                document.getElementById(
                    "global-search"
                );


            const results =
                document.getElementById(
                    "search-results"
                );


            if (
                !input
                ||
                !results
            ) {
                return;
            }


            input.addEventListener(
                "input",
                () => {

                    const query =
                        input.value.trim();


                    clearTimeout(
                        timer
                    );


                    if (
                        query.length < 2
                    ) {

                        hideResults(
                            results
                        );

                        return;

                    }


                    timer =
                        setTimeout(
                            () => {

                                performSearch(
                                    query,
                                    results
                                );

                            },
                            250
                        );

                }
            );


            input.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key
                        === "Escape"
                    ) {

                        input.value = "";

                        hideResults(
                            results
                        );

                    }

                }
            );


            document.addEventListener(
                "click",
                (event) => {

                    if (
                        !input.contains(
                            event.target
                        )
                        &&
                        !results.contains(
                            event.target
                        )
                    ) {

                        hideResults(
                            results
                        );

                    }

                }
            );

        }
    );

})();