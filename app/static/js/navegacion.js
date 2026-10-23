/* Controla los desplegables y el menú lateral de MovaGest.
   Conserva la navegación disponible cuando JavaScript no está activo. */
const botonMenu = document.querySelector(".boton-menu");
const botonCerrar = document.querySelector(".boton-cerrar-menu");
const fondoMenu = document.querySelector(".menu-overlay");
const navegacion = document.querySelector("#navegacion-principal");
const gruposMenu = document.querySelectorAll(".menu-grupo");
const menusAcciones = document.querySelectorAll(".acciones-mas");
const vistaMovil = window.matchMedia("(max-width: 47.999rem)");

function cerrarDesplegables(excepto) {
    gruposMenu.forEach((grupo) => {
        if (grupo !== excepto) {
            grupo.open = false;
        }
    });
}

function cerrarMenusAcciones(excepto) {
    menusAcciones.forEach((menu) => {
        if (menu !== excepto) {
            menu.open = false;
        }
    });
}

function cambiarMenuMovil(abrir, devolverFoco = true) {
    document.documentElement.classList.toggle("menu-abierto", abrir);
    botonMenu.setAttribute("aria-expanded", String(abrir));
    navegacion.setAttribute("aria-hidden", String(!abrir));
    navegacion.inert = !abrir;

    if (abrir) {
        setTimeout(() => navegacion.querySelector("a[href]")?.focus(), 0);
    } else {
        document.body.style.removeProperty("overflow");
        cerrarDesplegables();
        if (devolverFoco && vistaMovil.matches) {
            botonMenu.focus();
        }
    }
}
botonMenu.addEventListener("click", () => {
    cambiarMenuMovil(botonMenu.getAttribute("aria-expanded") !== "true", false);
});
botonCerrar.addEventListener("click", () => cambiarMenuMovil(false));
fondoMenu.addEventListener("click", () => cambiarMenuMovil(false));
gruposMenu.forEach((grupo) => {
    grupo.addEventListener("toggle", () => {
        if (grupo.open) {
            cerrarDesplegables(grupo);
        }
    });
});
menusAcciones.forEach((menu) => {
    menu.addEventListener("toggle", () => {
        if (menu.open) {
            cerrarMenusAcciones(menu);
        }
    });
});
document.addEventListener("click", (evento) => {
    if (!evento.target.closest(".menu-grupo")) {
        cerrarDesplegables();
    }
    if (!evento.target.closest(".acciones-mas")) {
        cerrarMenusAcciones();
    }
});
document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") {
        return;
    }
    const menuAccionAbierto = document.querySelector(".acciones-mas[open]");
    if (menuAccionAbierto) {
        menuAccionAbierto.querySelector("summary").focus();
        cerrarMenusAcciones();
        return;
    }
    if (vistaMovil.matches && botonMenu.getAttribute("aria-expanded") === "true") {
        cambiarMenuMovil(false);
    } else {
        gruposMenu.forEach((grupo) => {
            if (grupo.open) {
                grupo.querySelector("summary").focus();
            }
        });
        cerrarDesplegables();
    }
});
vistaMovil.addEventListener("change", (evento) => {
    if (evento.matches) {
        cambiarMenuMovil(false, false);
    } else {
        document.documentElement.classList.remove("menu-abierto");
        botonMenu.setAttribute("aria-expanded", "false");
        navegacion.setAttribute("aria-hidden", "false");
        navegacion.inert = false;
        document.body.style.removeProperty("overflow");
    }
});

if (vistaMovil.matches) {
    cambiarMenuMovil(false, false);
}
