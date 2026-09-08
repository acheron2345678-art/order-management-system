(() => {


    function clamp(
        value,
        min,
        max
    ) {

        if (
            Number.isNaN(
                value
            )
        ) {
            return min;
        }


        return Math.min(
            max,
            Math.max(
                min,
                value
            )
        );

    }



    /*
    ==========================================
    QUANTITY STEPPERS
    ==========================================
    */

    function setupQuantitySteppers() {


        document
            .querySelectorAll(
                "[data-quantity-stepper]"
            )
            .forEach(
                function (stepper) {


                    const input =
                        stepper.querySelector(
                            'input[type="number"]'
                        );


                    const decrease =
                        stepper.querySelector(
                            "[data-qty-decrease]"
                        );


                    const increase =
                        stepper.querySelector(
                            "[data-qty-increase]"
                        );


                    if (
                        !input
                        ||
                        !decrease
                        ||
                        !increase
                    ) {

                        return;

                    }


                    const minimum =
                        Number(
                            input.min || 0
                        );


                    const maximum =
                        Number(
                            input.max
                            ||
                            Number.MAX_SAFE_INTEGER
                        );


                    function setValue(
                        nextValue
                    ) {


                        const value =
                            clamp(
                                Number(
                                    nextValue
                                ),
                                minimum,
                                maximum
                            );


                        input.value =
                            String(
                                value
                            );


                    }


                    decrease.addEventListener(
                        "click",
                        function () {


                            setValue(
                                Number(
                                    input.value
                                )
                                -
                                1
                            );


                        }
                    );


                    increase.addEventListener(
                        "click",
                        function () {


                            setValue(
                                Number(
                                    input.value
                                )
                                +
                                1
                            );


                        }
                    );


                    input.addEventListener(
                        "change",
                        function () {


                            setValue(
                                Number(
                                    input.value
                                )
                            );


                        }
                    );


                }
            );


    }



    /*
    ==========================================
    FORM LOADING STATES
    ==========================================
    */

    function setupLoadingForms() {


        document
            .querySelectorAll(
                "[data-loading-form]"
            )
            .forEach(
                function (form) {


                    form.addEventListener(
                        "submit",
                        function () {


                            const button =
                                form.querySelector(
                                    'button[type="submit"]'
                                );


                            if (!button) {

                                return;

                            }


                            if (
                                button.dataset.loading
                                ===
                                "true"
                            ) {

                                return;

                            }


                            button.dataset.loading =
                                "true";


                            button.dataset.originalText =
                                button.textContent.trim();


                            button.textContent =
                                button.dataset.loadingText
                                ||
                                "Please wait...";


                            button.disabled =
                                true;


                        }
                    );


                }
            );


    }



    /*
    ==========================================
    AUTO DISMISS ALERTS
    ==========================================
    */

    function setupAutoDismissAlerts() {


        const alerts =
            document.querySelectorAll(
                "[data-auto-dismiss-alert]"
            );


        alerts.forEach(
            function (alert) {


                window.setTimeout(
                    function () {


                        alert.classList.add(
                            "sw-alert-hide"
                        );


                        window.setTimeout(
                            function () {


                                alert.remove();


                            },
                            220
                        );


                    },
                    6000
                );


            }
        );


    }



    /*
    ==========================================
    MENU SEARCH SHORTCUT
    ==========================================
    */

    function setupSearchShortcut() {


        document.addEventListener(
            "keydown",
            function (event) {


                const activeElement =
                    document.activeElement;


                const typing =
                    activeElement
                    &&
                    (
                        activeElement.tagName
                        ===
                        "INPUT"
                        ||
                        activeElement.tagName
                        ===
                        "TEXTAREA"
                    );


                if (
                    event.key === "/"
                    &&
                    !typing
                ) {


                    const search =
                        document.querySelector(
                            ".sw-topbar-search input"
                        );


                    if (!search) {

                        return;

                    }


                    event.preventDefault();


                    search.focus();


                }


            }
        );


    }



    /*
    ==========================================
    MY ORDERS DATATABLE
    ==========================================
    */

    function setupOrdersDataTable() {


        const table =
            document.getElementById(
                "swiggy-orders-table"
            );


        if (!table) {

            return;

        }



        if (
            typeof window.jQuery
            ===
            "undefined"
        ) {


            console.error(
                "Swiggy DataTable error: jQuery is not loaded."
            );


            return;

        }



        if (
            typeof $.fn.DataTable
            ===
            "undefined"
        ) {


            console.error(
                "Swiggy DataTable error: DataTables is not loaded."
            );


            return;

        }



        if (
            $.fn.DataTable.isDataTable(
                "#swiggy-orders-table"
            )
        ) {


            return;

        }



        const ordersTable =
            $(
                "#swiggy-orders-table"
            ).DataTable(
                {


                    paging:
                        true,


                    pageLength:
                        10,


                    lengthChange:
                        true,


                    lengthMenu: [

                        [
                            5,
                            10,
                            25,
                            50
                        ],

                        [
                            5,
                            10,
                            25,
                            50
                        ]

                    ],



                    searching:
                        true,


                    ordering:
                        true,



                    /*
                    Newest order first
                    */

                    order: [

                        [
                            2,
                            "desc"
                        ]

                    ],



                    info:
                        true,


                    autoWidth:
                        false,



                    columnDefs: [


                        {
                            targets:
                                0,

                            searchable:
                                true,

                            orderable:
                                true
                        },


                        {
                            targets:
                                1,

                            searchable:
                                true,

                            orderable:
                                true
                        },


                        {
                            targets:
                                2,

                            searchable:
                                true,

                            orderable:
                                true
                        },


                        {
                            targets:
                                3,

                            searchable:
                                true,

                            orderable:
                                true
                        },


                        {
                            targets:
                                4,

                            searchable:
                                true,

                            orderable:
                                true
                        },


                        {
                            targets:
                                5,

                            searchable:
                                false,

                            orderable:
                                false
                        }


                    ],



                    layout: {


                        topStart:
                            "pageLength",


                        topEnd:
                            "search",


                        bottomStart:
                            "info",


                        bottomEnd:
                            "paging"


                    },



                    language: {


                        search:
                            "",


                        searchPlaceholder:
                            "Search orders...",


                        lengthMenu:
                            "Show _MENU_ orders",


                        info:
                            "Showing _START_ to _END_ of _TOTAL_ orders",


                        infoEmpty:
                            "Showing 0 orders",


                        infoFiltered:
                            "(filtered from _MAX_ total orders)",


                        zeroRecords:
                            "No matching orders found",


                        emptyTable:
                            "No Swiggy orders available",


                        paginate: {


                            first:
                                "First",


                            previous:
                                "Previous",


                            next:
                                "Next",


                            last:
                                "Last"


                        }


                    }


                }
            );



        console.log(
            "Swiggy My Orders DataTable initialized:",
            ordersTable
        );


    }



    /*
    ==========================================
    INITIALIZE
    ==========================================
    */

    function initializeSwiggyPage() {


        setupQuantitySteppers();


        setupLoadingForms();


        setupAutoDismissAlerts();


        setupSearchShortcut();


        setupOrdersDataTable();


    }



    if (
        document.readyState
        ===
        "loading"
    ) {


        document.addEventListener(
            "DOMContentLoaded",
            initializeSwiggyPage
        );


    } else {


        initializeSwiggyPage();


    }


})();