import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class MovementFlowTest extends BaseTest {

    private static String movementId;

    @Test
    @Order(1)
    public void step1_createMovement() {
        movementId = given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 10, \"warehouseToId\": 20, " +
                  "\"productId\": 500, \"quantity\": 100, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(201)
            .body("status", equalTo("CREATED"))
            .extract().path("id");
    }

    @Test
    @Order(2)
    public void step2_getMovement_statusCreated() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/movements/{id}", movementId)
        .then()
            .statusCode(200)
            .body("id", equalTo(movementId))
            .body("status", equalTo("CREATED"))
            .body("quantity", equalTo(100));
    }

    @Test
    @Order(3)
    public void step3_approveMovement() {
        given()
            .spec(managerSpec)
        .when()
            .put("/movements/{id}/approve", movementId)
        .then()
            .statusCode(200)
            .body("status", equalTo("APPROVED"));
    }

    @Test
    @Order(4)
    public void step4_completeMovement() {
        given()
            .spec(operatorSpec)
            .body("{\"actualQuantity\": 98}")
        .when()
            .put("/movements/{id}/complete", movementId)
        .then()
            .statusCode(200)
            .body("status", equalTo("COMPLETED"))
            .body("actualQuantity", equalTo(98));
    }

    @Test
    @Order(5)
    public void step5_getMovement_statusCompleted() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/movements/{id}", movementId)
        .then()
            .statusCode(200)
            .body("status", equalTo("COMPLETED"))
            .body("actualQuantity", equalTo(98));
    }

    @Test
    @Order(6)
    public void step6_cannotModifyCompletedMovement() {
        given()
            .spec(managerSpec)
        .when()
            .put("/movements/{id}/approve", movementId)
        .then()
            .statusCode(409)
            .body("error", equalTo("INVALID_STATE_TRANSITION"));
    }
}
