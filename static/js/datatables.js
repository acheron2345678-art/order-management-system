document.addEventListener(
    "DOMContentLoaded",
    () => {

        const table =
            document.getElementById(
                "ordersTable"
            );


        if (!table) {
            return;
        }



        // =========================================
        // DATATABLES CHECK
        // =========================================

        if (
            typeof DataTable
            ===
            "undefined"
        ) {

            console.error(
                "DataTables v2 is not loaded."
            );

            return;
        }



        if (
            DataTable.isDataTable(
                "#ordersTable"
            )
        ) {
            return;
        }



        // =========================================
        // TABLE INFORMATION
        // =========================================

        const exportEnabled =
            table.dataset.exportEnabled
            ===
            "true";


        const platformName =
            table.dataset.platform
            ||
            "Orders";


        const exportBaseFilename =
            table.dataset.exportFilename
            ||
            "orders";


        const today =
            new Date()
                .toISOString()
                .slice(
                    0,
                    10
                );


        const exportFilename =
            `${exportBaseFilename}-${today}`;



        // =========================================
        // DATATABLES LAYOUT
        // =========================================

        const topStartLayout = [
            "pageLength"
        ];



        // =========================================
        // ADMIN EXCEL EXPORT
        // =========================================

        if (exportEnabled) {

            const buttonsAvailable =
                typeof DataTable.Buttons
                !==
                "undefined";


            const jsZipAvailable =
                typeof JSZip
                !==
                "undefined";


            if (
                buttonsAvailable
                &&
                jsZipAvailable
            ) {

                topStartLayout.push(
                    {
                        buttons: [

                            {
                                extend:
                                    "excelHtml5",

                                text:
                                    "Export Excel",

                                title:
                                    `${platformName} Orders`,

                                filename:
                                    exportFilename,

                                sheetName:
                                    "Orders",

                                className:
                                    "btn btn-success",

                                autoFilter:
                                    true,

                                exportOptions: {

                                    // =================================
                                    // EXPORT EVERYTHING EXCEPT ACTIONS
                                    // =================================

                                    columns: [
                                        0,
                                        1,
                                        2,
                                        3,
                                        4,
                                        5,
                                        6,
                                        7
                                    ],


                                    // =================================
                                    // EXACT CURRENT TABLE STATE
                                    // =================================

                                    modifier: {

                                        search:
                                            "applied",

                                        order:
                                            "applied",

                                        page:
                                            "all",

                                    },


                                    // =================================
                                    // SECURITY
                                    // =================================
                                    // Prevent user supplied cell values
                                    // from becoming Excel formulas.

                                    escapeExcelFormula:
                                        true,


                                    // =================================
                                    // CLEAN HTML FOR EXCEL
                                    // =================================

                                    stripHtml:
                                        true,

                                    stripNewlines:
                                        false,

                                    trim:
                                        true,


                                    format: {

                                        body: function (
                                            data,
                                            row,
                                            column,
                                            node
                                        ) {

                                            if (!node) {

                                                return (
                                                    data
                                                    ??
                                                    ""
                                                );

                                            }


                                            // =========================
                                            // CLIENT COLUMN
                                            // =========================
                                            // Preserve username and email
                                            // as readable information.

                                            if (
                                                column
                                                ===
                                                1
                                            ) {

                                                const username =
                                                    node
                                                        .querySelector(
                                                            ".fw-semibold"
                                                        );


                                                const email =
                                                    node
                                                        .querySelector(
                                                            ".text-body-secondary"
                                                        );


                                                if (
                                                    username
                                                    &&
                                                    email
                                                ) {

                                                    return (
                                                        `${username.textContent.trim()}`
                                                        +
                                                        "\n"
                                                        +
                                                        `${email.textContent.trim()}`
                                                    );

                                                }

                                            }


                                            // =========================
                                            // AMOUNT COLUMN
                                            // =========================
                                            // Use displayed value so the
                                            // exported table matches what
                                            // the admin sees.

                                            if (
                                                column
                                                ===
                                                5
                                            ) {

                                                return (
                                                    node
                                                        .textContent
                                                        .trim()
                                                );

                                            }


                                            // =========================
                                            // DEFAULT
                                            // =========================

                                            return (
                                                node
                                                    .textContent
                                                    .trim()
                                            );

                                        },

                                    },

                                },

                            },

                        ],
                    }
                );

            }

            else {

                console.error(
                    "Excel export dependencies "
                    +
                    "are not loaded."
                );

            }

        }



        // =========================================
        // INITIALISE DATATABLE
        // =========================================

        const dataTable =
            new DataTable(
                "#ordersTable",
                {

                    // =================================
                    // PAGINATION
                    // =================================

                    paging:
                        true,


                    pageLength:
                        10,


                    lengthMenu: [
                        10,
                        25,
                        50,
                        100
                    ],



                    // =================================
                    // ORDERING
                    // =================================

                    ordering: {

                        indicator:
                            true,

                        handler:
                            true,

                    },


                    order: [

                        [
                            7,
                            "desc"
                        ],

                        [
                            0,
                            "desc"
                        ]

                    ],



                    // =================================
                    // SEARCH
                    // =================================

                    searching:
                        true,



                    // =================================
                    // TABLE INFORMATION
                    // =================================

                    info:
                        true,


                    processing:
                        false,



                    // =================================
                    // WIDTH / SCROLL
                    // =================================

                    scrollX:
                        true,


                    autoWidth:
                        false,



                    // =================================
                    // COLUMN CONFIGURATION
                    // =================================

                    columnDefs: [

                        {
                            targets:
                                0,

                            type:
                                "num",
                        },


                        {
                            targets:
                                5,

                            type:
                                "num",
                        },


                        {
                            targets:
                                7,

                            type:
                                "date",
                        },


                        {
                            targets:
                                -1,

                            orderable:
                                false,

                            searchable:
                                false,
                        },

                    ],



                    // =================================
                    // LAYOUT
                    // =================================

                    layout: {

                        topStart:
                            topStartLayout,


                        topEnd:
                            "search",


                        bottomStart:
                            "info",


                        bottomEnd:
                            "paging",

                    },



                    // =================================
                    // LANGUAGE
                    // =================================

                    language: {

                        search:
                            "Search table:",


                        searchPlaceholder:
                            "Search these orders...",


                        lengthMenu:
                            "Show _MENU_ orders",


                        info:
                            "Showing _START_ to _END_ of _TOTAL_ orders",


                        infoEmpty:
                            "Showing 0 to 0 of 0 orders",


                        emptyTable:
                            "No orders found",


                        zeroRecords:
                            "No matching orders found",


                        paginate: {

                            first:
                                "First",

                            previous:
                                "Previous",

                            next:
                                "Next",

                            last:
                                "Last",

                        },

                    },

                }
            );



        // =========================================
        // SORTABLE COLUMN TOOLTIP
        // =========================================

        table
            .querySelectorAll(
                "thead th"
            )
            .forEach(
                (
                    header,
                    index
                ) => {

                    if (
                        index
                        !==
                        8
                    ) {

                        header
                            .classList
                            .add(
                                "sortable-column"
                            );


                        header.title =
                            "Click to sort";

                    }

                }
            );



        // =========================================
        // COLUMN WIDTH RECALCULATION
        // =========================================

        requestAnimationFrame(
            () => {

                dataTable
                    .columns
                    .adjust();

            }
        );

    }
);