import { Controller } from '@nestjs/common';

@Controller('store')
export class StoreController {
    // This controller is design for store info api use
    // should have following api
    // basic
    // get /store/list - get store list
    // get /store/:id - get store detail
    // special
    // post /store/open - use time or week to get opening store
    // post /store/mask - use storeId to get all mask info (by maskId)
    // post /store/kind/price
    // post /store/user_purchase/date
    
}
