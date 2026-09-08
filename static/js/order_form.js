document.addEventListener(
    "DOMContentLoaded",
    function () {

        const container =
            document.getElementById(
                "order-products"
            );

        const addButton =
            document.getElementById(
                "add-product-row"
            );

        const orderTotalDisplay =
            document.getElementById(
                "order-total"
            );

        const orderForm =
            document.getElementById(
                "order-form"
            );


        if (
            !container
            ||
            !addButton
            ||
            !orderTotalDisplay
        ) {
            return;
        }


        function formatMoney(
            value
        ) {

            const amount =
                Number(
                    value
                );


            if (
                Number.isNaN(
                    amount
                )
            ) {

                return "₹0.00";

            }


            return (
                "₹"
                +
                amount.toLocaleString(
                    "en-IN",
                    {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }
                )
            );

        }


        function getRows() {

            return Array.from(
                container.querySelectorAll(
                    ".order-product-row"
                )
            );

        }


        function getSelectedProductIds() {

            const selectedIds =
                new Set();


            getRows().forEach(
                function (row) {

                    const select =
                        row.querySelector(
                            ".product-select"
                        );


                    if (
                        select
                        &&
                        select.value
                    ) {

                        selectedIds.add(
                            select.value
                        );

                    }

                }
            );


            return selectedIds;

        }


        function updateProductOptions() {

            const rows =
                getRows();


            rows.forEach(
                function (currentRow) {

                    const currentSelect =
                        currentRow.querySelector(
                            ".product-select"
                        );


                    if (!currentSelect) {
                        return;
                    }


                    const currentValue =
                        currentSelect.value;


                    const selectedByOtherRows =
                        new Set();


                    rows.forEach(
                        function (otherRow) {

                            if (
                                otherRow
                                === currentRow
                            ) {
                                return;
                            }


                            const otherSelect =
                                otherRow.querySelector(
                                    ".product-select"
                                );


                            if (
                                otherSelect
                                &&
                                otherSelect.value
                            ) {

                                selectedByOtherRows.add(
                                    otherSelect.value
                                );

                            }

                        }
                    );


                    Array.from(
                        currentSelect.options
                    ).forEach(
                        function (option) {

                            if (
                                !option.value
                            ) {
                                return;
                            }


                            const stock =
                                Number(
                                    option.dataset.stock
                                );


                            const noStock =
                                Number.isNaN(stock)
                                ||
                                stock <= 0;


                            const selectedElsewhere =
                                selectedByOtherRows.has(
                                    option.value
                                );


                            option.disabled =
                                noStock
                                ||
                                selectedElsewhere;

                        }
                    );


                    if (currentValue) {

                        const currentOption =
                            Array.from(
                                currentSelect.options
                            ).find(
                                function (option) {

                                    return (
                                        option.value
                                        === currentValue
                                    );

                                }
                            );


                        if (currentOption) {

                            const stock =
                                Number(
                                    currentOption.dataset.stock
                                );


                            currentOption.disabled =
                                Number.isNaN(stock)
                                ||
                                stock <= 0;

                        }

                    }

                }
            );

        }


        function updateRow(
            row
        ) {

            const select =
                row.querySelector(
                    ".product-select"
                );

            const quantityInput =
                row.querySelector(
                    ".quantity-input"
                );

            const lineTotalDisplay =
                row.querySelector(
                    ".line-total"
                );

            const stockMessage =
                row.querySelector(
                    ".product-stock-message"
                );


            if (
                !select
                ||
                !quantityInput
                ||
                !lineTotalDisplay
            ) {
                return 0;
            }


            const selectedOption =
                select.options[
                    select.selectedIndex
                ];


            if (
                !selectedOption
                ||
                !selectedOption.value
            ) {

                quantityInput.removeAttribute(
                    "max"
                );

                lineTotalDisplay.value =
                    "₹0.00";


                if (stockMessage) {

                    stockMessage.textContent =
                        "Select a product to view stock information.";

                    stockMessage.classList.remove(
                        "text-danger",
                        "text-warning",
                        "text-success"
                    );

                    stockMessage.classList.add(
                        "text-body-secondary"
                    );

                }


                return 0;

            }


            const price =
                Number(
                    selectedOption.dataset.price
                );


            const stock =
                Number(
                    selectedOption.dataset.stock
                );


            if (
                Number.isNaN(price)
                ||
                Number.isNaN(stock)
            ) {

                lineTotalDisplay.value =
                    "₹0.00";

                return 0;

            }


            quantityInput.max =
                stock;


            let quantity =
                Number(
                    quantityInput.value
                );


            if (
                !Number.isInteger(
                    quantity
                )
                ||
                quantity < 1
            ) {

                quantity = 1;

                quantityInput.value =
                    1;

            }


            if (
                stock > 0
                &&
                quantity > stock
            ) {

                quantity =
                    stock;

                quantityInput.value =
                    stock;

            }


            const lineTotal =
                price
                *
                quantity;


            lineTotalDisplay.value =
                formatMoney(
                    lineTotal
                );


            if (stockMessage) {

                stockMessage.classList.remove(
                    "text-body-secondary",
                    "text-danger",
                    "text-warning",
                    "text-success"
                );


                if (stock <= 0) {

                    stockMessage.textContent =
                        "Out of stock";

                    stockMessage.classList.add(
                        "text-danger"
                    );

                } else if (
                    quantity >= stock
                ) {

                    stockMessage.textContent =
                        `${stock} unit${stock === 1 ? "" : "s"} available — all stock selected`;

                    stockMessage.classList.add(
                        "text-warning"
                    );

                } else {

                    stockMessage.textContent =
                        `${stock} unit${stock === 1 ? "" : "s"} available`;

                    stockMessage.classList.add(
                        "text-success"
                    );

                }

            }


            return lineTotal;

        }


        function updateOrderTotal() {

            let total =
                0;


            getRows().forEach(
                function (row) {

                    total +=
                        updateRow(
                            row
                        );

                }
            );


            orderTotalDisplay.textContent =
                formatMoney(
                    total
                );


            updateProductOptions();

        }


        function resetRow(
            row
        ) {

            const select =
                row.querySelector(
                    ".product-select"
                );

            const quantity =
                row.querySelector(
                    ".quantity-input"
                );

            const lineTotal =
                row.querySelector(
                    ".line-total"
                );

            const stockMessage =
                row.querySelector(
                    ".product-stock-message"
                );


            if (select) {

                select.value =
                    "";

            }


            if (quantity) {

                quantity.value =
                    1;

                quantity.removeAttribute(
                    "max"
                );

            }


            if (lineTotal) {

                lineTotal.value =
                    "₹0.00";

            }


            if (stockMessage) {

                stockMessage.textContent =
                    "Select a product to view stock information.";

                stockMessage.className =
                    "product-stock-message small text-body-secondary mt-2";

            }

        }


        function attachRowEvents(
            row
        ) {

            const select =
                row.querySelector(
                    ".product-select"
                );

            const quantity =
                row.querySelector(
                    ".quantity-input"
                );

            const removeButton =
                row.querySelector(
                    ".remove-product-row"
                );


            if (select) {

                select.addEventListener(
                    "change",
                    function () {

                        const selected =
                            select.options[
                                select.selectedIndex
                            ];


                        if (
                            selected
                            &&
                            selected.value
                        ) {

                            const stock =
                                Number(
                                    selected.dataset.stock
                                );


                            if (
                                !Number.isNaN(stock)
                                &&
                                stock > 0
                            ) {

                                quantity.max =
                                    stock;


                                if (
                                    Number(
                                        quantity.value
                                    )
                                    >
                                    stock
                                ) {

                                    quantity.value =
                                        stock;

                                }

                            }

                        }


                        updateOrderTotal();

                    }
                );

            }


            if (quantity) {

                quantity.addEventListener(
                    "input",
                    function () {

                        updateOrderTotal();

                    }
                );


                quantity.addEventListener(
                    "change",
                    function () {

                        updateOrderTotal();

                    }
                );

            }


            if (removeButton) {

                removeButton.addEventListener(
                    "click",
                    function () {

                        const rows =
                            getRows();


                        if (
                            rows.length <= 1
                        ) {

                            resetRow(
                                row
                            );

                            updateOrderTotal();

                            return;

                        }


                        row.remove();


                        updateOrderTotal();

                    }
                );

            }

        }


        addButton.addEventListener(
            "click",
            function () {

                const rows =
                    getRows();


                if (
                    rows.length === 0
                ) {
                    return;
                }


                const sourceRow =
                    rows[0];


                const newRow =
                    sourceRow.cloneNode(
                        true
                    );


                resetRow(
                    newRow
                );


                container.appendChild(
                    newRow
                );


                attachRowEvents(
                    newRow
                );


                updateOrderTotal();


                const select =
                    newRow.querySelector(
                        ".product-select"
                    );


                if (select) {

                    select.focus();

                }

            }
        );


        getRows().forEach(
            function (row) {

                attachRowEvents(
                    row
                );

            }
        );


        if (orderForm) {

            orderForm.addEventListener(
                "submit",
                function (event) {

                    const rows =
                        getRows();


                    if (
                        rows.length === 0
                    ) {

                        event.preventDefault();

                        alert(
                            "Add at least one product."
                        );

                        return;

                    }


                    let validRows =
                        0;


                    let invalidStock =
                        false;


                    const selectedProductIds =
                        new Set();


                    for (
                        const row
                        of rows
                    ) {

                        const select =
                            row.querySelector(
                                ".product-select"
                            );

                        const quantityInput =
                            row.querySelector(
                                ".quantity-input"
                            );


                        if (
                            !select
                            ||
                            !select.value
                        ) {

                            event.preventDefault();

                            select?.focus();

                            alert(
                                "Select a product for every row."
                            );

                            return;

                        }


                        const productId =
                            select.value;


                        if (
                            selectedProductIds.has(
                                productId
                            )
                        ) {

                            event.preventDefault();

                            select.focus();

                            alert(
                                "The same product cannot be added more than once. Change the quantity instead."
                            );

                            return;

                        }


                        selectedProductIds.add(
                            productId
                        );


                        const selected =
                            select.options[
                                select.selectedIndex
                            ];


                        const stock =
                            Number(
                                selected.dataset.stock
                            );


                        const quantity =
                            Number(
                                quantityInput.value
                            );


                        if (
                            !Number.isInteger(
                                quantity
                            )
                            ||
                            quantity <= 0
                        ) {

                            event.preventDefault();

                            quantityInput.focus();

                            alert(
                                "Quantity must be greater than 0."
                            );

                            return;

                        }


                        if (
                            Number.isNaN(
                                stock
                            )
                            ||
                            quantity > stock
                        ) {

                            invalidStock =
                                true;

                            quantityInput.focus();

                            break;

                        }


                        validRows++;

                    }


                    if (
                        invalidStock
                    ) {

                        event.preventDefault();

                        alert(
                            "One or more products do not have enough stock."
                        );

                        return;

                    }


                    if (
                        validRows === 0
                    ) {

                        event.preventDefault();

                        alert(
                            "Add at least one product."
                        );

                    }

                }
            );

        }


        updateOrderTotal();

    }
);