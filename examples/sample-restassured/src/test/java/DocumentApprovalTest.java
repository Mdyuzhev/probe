import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class DocumentApprovalTest extends BaseTest {

    private static String documentId;

    @Test
    @Order(1)
    public void createDocument_asDraft() {
        documentId = given()
            .spec(operatorSpec)
            .body("{\"type\": \"TRANSFER_ACT\", \"movementId\": \"mvmt-001\", " +
                  "\"date\": \"2025-02-01\", \"items\": [{\"productId\": 1, \"quantity\": 10}]}")
        .when()
            .post("/documents")
        .then()
            .statusCode(201)
            .body("status", equalTo("DRAFT"))
            .body("type", equalTo("TRANSFER_ACT"))
            .extract().path("id");
    }

    @Test
    @Order(2)
    public void approveDocument_operatorForbidden_returns403() {
        given()
            .spec(operatorSpec)
        .when()
            .put("/documents/{id}/approve", documentId)
        .then()
            .statusCode(403)
            .body("error", equalTo("ACCESS_DENIED"));
    }

    @Test
    @Order(3)
    public void approveDocument_managerAllowed_returns200() {
        given()
            .spec(managerSpec)
        .when()
            .put("/documents/{id}/approve", documentId)
        .then()
            .statusCode(200)
            .body("status", equalTo("APPROVED"))
            .body("approvedBy", notNullValue())
            .body("approvedAt", notNullValue());
    }

    @Test
    @Order(4)
    public void rejectDocument_afterApproval_returns409() {
        given()
            .spec(managerSpec)
            .body("{\"reason\": \"incorrect data\"}")
        .when()
            .put("/documents/{id}/reject", documentId)
        .then()
            .statusCode(409)
            .body("error", equalTo("INVALID_STATE_TRANSITION"));
    }

    @Test
    public void listDocuments_filterByStatus() {
        given()
            .spec(managerSpec)
            .queryParam("status", "DRAFT")
        .when()
            .get("/documents")
        .then()
            .statusCode(200)
            .body("content", notNullValue())
            .body("content.status", everyItem(equalTo("DRAFT")));
    }
}
