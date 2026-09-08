(() => {


    /*
    ==========================================
    LOADING BUTTONS
    ==========================================
    */

    function setupLoadingForms() {


        const forms =
            document.querySelectorAll(
                "[data-loading-form]"
            );


        forms.forEach(
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
                            "in-alert-hide"
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
    SERVICE SEARCH SHORTCUT

    Press "/" anywhere on the page
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
                            ".in-topbar-search input"
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
    INSIGHTS PROJECT DATATABLE
    ==========================================
    */

    function setupProjectsDataTable() {


        const table =
            document.getElementById(
                "insights-projects-table"
            );


        /*
        Page is not My Projects
        */

        if (!table) {


            return;


        }



        /*
        Check jQuery
        */

        if (
            typeof window.jQuery
            ===
            "undefined"
        ) {


            console.error(
                "Insights DataTable error: jQuery is not loaded."
            );


            return;


        }



        /*
        Check DataTables
        */

        if (
            typeof $.fn.DataTable
            ===
            "undefined"
        ) {


            console.error(
                "Insights DataTable error: DataTables is not loaded."
            );


            return;


        }



        /*
        Prevent duplicate initialization
        */

        if (
            $.fn.DataTable.isDataTable(
                "#insights-projects-table"
            )
        ) {


            return;


        }



        /*
        Initialize DataTable
        */

        const tableInstance =
            $(
                "#insights-projects-table"
            ).DataTable(
                {


                    /*
                    PAGINATION
                    */

                    paging:
                        true,


                    pageLength:
                        10,


                    lengthChange:
                        true,


                    lengthMenu: [

                        [5, 10, 25, 50],

                        [5, 10, 25, 50]

                    ],



                    /*
                    SEARCH
                    */

                    searching:
                        true,



                    /*
                    SORTING
                    */

                    ordering:
                        true,


                    order: [

                        [
                            2,
                            "desc"
                        ]

                    ],



                    /*
                    INFORMATION
                    */

                    info:
                        true,



                    /*
                    RESPONSIVE WIDTH
                    */

                    autoWidth:
                        false,



                    /*
                    COLUMNS
                    */

                    columnDefs: [


                        /*
                        PROJECT
                        */

                        {

                            targets:
                                0,

                            searchable:
                                true,

                            orderable:
                                true

                        },


                        /*
                        CLIENT
                        */

                        {

                            targets:
                                1,

                            searchable:
                                true,

                            orderable:
                                true

                        },


                        /*
                        SUBMITTED DATE
                        */

                        {

                            targets:
                                2,

                            searchable:
                                true,

                            orderable:
                                true

                        },


                        /*
                        VALUE
                        */

                        {

                            targets:
                                3,

                            searchable:
                                true,

                            orderable:
                                true

                        },


                        /*
                        STATUS
                        */

                        {

                            targets:
                                4,

                            searchable:
                                true,

                            orderable:
                                true

                        },


                        /*
                        ACTION
                        */

                        {

                            targets:
                                5,

                            searchable:
                                false,

                            orderable:
                                false

                        }


                    ],



                    /*
                    DATATABLE LAYOUT
                    */

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



                    /*
                    TEXT
                    */

                    language: {


                        search:
                            "",


                        searchPlaceholder:
                            "Search projects...",


                        lengthMenu:
                            "Show _MENU_ projects",


                        info:
                            "Showing _START_ to _END_ of _TOTAL_ projects",


                        infoEmpty:
                            "Showing 0 projects",


                        infoFiltered:
                            "(filtered from _MAX_ total projects)",


                        zeroRecords:
                            "No matching projects found",


                        emptyTable:
                            "No Insights projects available",


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
            "Insights Projects DataTable initialized:",
            tableInstance
        );


    }



    /*
    ==========================================
    PAGE INITIALIZATION
    ==========================================
    */

    function initializeInsightsPage() {


        setupLoadingForms();


        setupAutoDismissAlerts();


        setupSearchShortcut();


        setupProjectsDataTable();


    }



    /*
    ==========================================
    RUN WHEN DOM IS READY
    ==========================================
    */

    if (
        document.readyState
        ===
        "loading"
    ) {


        document.addEventListener(
            "DOMContentLoaded",
            initializeInsightsPage
        );


    } else {


        initializeInsightsPage();


    }


})();