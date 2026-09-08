document.addEventListener("DOMContentLoaded", () => {

    const searchInput =
        document.getElementById("product-search");

    const clearButton =
        document.getElementById("clear-product-search");

    const productsGrid =
        document.getElementById("products-grid");

    const productItems =
        document.querySelectorAll(".product-item");

    const noResults =
        document.getElementById("product-no-results");

    const resultCount =
        document.getElementById("product-result-count");

    const resultLabel =
        document.getElementById("product-result-label");


    if (
        !searchInput ||
        !productsGrid ||
        productItems.length === 0
    ) {
        return;
    }


    function updateCount(count) {

        if (resultCount) {
            resultCount.textContent = count;
        }

        if (resultLabel) {
            resultLabel.textContent =
                count === 1
                    ? ""
                    : "s";
        }

    }


    function filterProducts() {

        const query =
            searchInput.value
                .trim()
                .toLowerCase();


        let visibleCount = 0;


        productItems.forEach((product) => {

            const name =
                product.dataset.name || "";

            const description =
                product.dataset.description || "";

            const platform =
                product.dataset.platform || "";


            const matches =
                name.includes(query) ||
                description.includes(query) ||
                platform.includes(query);


            if (matches) {

                product.classList.remove("d-none");

                visibleCount++;

            } else {

                product.classList.add("d-none");

            }

        });


        updateCount(
            visibleCount
        );


        if (visibleCount === 0) {

            productsGrid.classList.add(
                "d-none"
            );

            if (noResults) {
                noResults.classList.remove(
                    "d-none"
                );
            }

        } else {

            productsGrid.classList.remove(
                "d-none"
            );

            if (noResults) {
                noResults.classList.add(
                    "d-none"
                );
            }

        }

    }


    searchInput.addEventListener(
        "input",
        filterProducts
    );


    if (clearButton) {

        clearButton.addEventListener(
            "click",
            () => {

                searchInput.value = "";

                filterProducts();

                searchInput.focus();

            }
        );

    }


    searchInput.addEventListener(
        "keydown",
        (event) => {

            if (event.key === "Escape") {

                searchInput.value = "";

                filterProducts();

            }

        }
    );

});